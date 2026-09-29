from django.db.models import Count, F, Q
from django.contrib.auth import authenticate, get_user_model
import django_filters
from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework import serializers as drf_serializers
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action, permission_classes
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import Category, Favorite, Recipe
from .roles import is_moderator_or_above
from .permissions import CanCreateRecipe, CanManageCategories, IsAuthorOrModeratorOrReadOnly, IsOwnerOrReadOnly
from .serializers import (
    CategorySerializer,
    FavoriteCreateSerializer,
    FavoriteSerializer,
    RecipeDetailSerializer,
    RecipeListSerializer,
    RecipeWriteSerializer,
    RegisterSerializer,
    UserSerializer,
)

User = get_user_model()


class RecipePagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 48


class MultiValueCharFilter(filters.Filter):
    """Matches a single value, or any-of when the query parameter repeats.

    The frontend sends one parameter per selected checkbox, so this has to
    accept ``?difficulty=easy`` as well as ``?difficulty=easy&difficulty=hard``.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("lookup_expr", "exact")
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value in django_filters.constants.EMPTY_VALUES:
            return qs

        # `value` is only the last value of a repeated parameter, so read the
        # full list straight off the request's query parameters.
        data = getattr(self.parent, "data", None)
        values = data.getlist(self.field_name) if hasattr(data, "getlist") else [value]
        values = [v for v in values if v not in django_filters.constants.EMPTY_VALUES]
        if not values:
            return qs

        lookup = f"{self.field_name}__{self.lookup_expr}"
        if len(values) == 1:
            return qs.filter(**{lookup: values[0]})
        query = Q()
        for item in values:
            query |= Q(**{lookup: item})
        return qs.filter(query)


class RecipeFilter(filters.FilterSet):
    """Filtering for the recipe list.

    `difficulty` and `category` accept repeated query values so the frontend
    can send multi-select checkboxes; the API matches any of them.
    """

    total_time = filters.NumberFilter(field_name="total_minutes", lookup_expr="lte")
    difficulty = MultiValueCharFilter(field_name="difficulty")
    category = MultiValueCharFilter(field_name="category")

    class Meta:
        model = Recipe
        fields = {
            "author__username": ["exact"],
            "cuisine": ["icontains"],
        }


class CategoryViewSet(viewsets.ModelViewSet):
    """Read-only for everyone; curators (moderators and admins) may write."""

    queryset = Category.objects.annotate(recipe_count=Count("recipes", filter=Q(recipes__published=True)))
    serializer_class = CategorySerializer
    pagination_class = None
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]
    permission_classes = [CanManageCategories]

    def list(self, request, *args, **kwargs):
        categories = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(categories, many=True)
        return Response(serializer.data)


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.select_related("author", "category").prefetch_related(
        "ingredients", "instructions", "favorited_by"
    ).annotate(total_minutes=F("preparation_time") + F("cooking_time"))
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = RecipeFilter
    search_fields = ["title", "description", "cuisine", "ingredients__name"]
    ordering_fields = ["created_at", "preparation_time", "cooking_time", "title", "total_minutes"]
    ordering = ["-created_at"]
    pagination_class = RecipePagination

    def get_queryset(self):
        """Visibility by role.

        Guests see published recipes only. Cooks additionally see their own
        drafts. Moderators and admins see everything, because reviewing
        unpublished submissions is part of the job.
        """
        qs = super().get_queryset()
        # Searching across a reverse relation can duplicate rows.
        if self.request.query_params.get("search"):
            qs = qs.distinct()

        user = self.request.user
        if is_moderator_or_above(user):
            return qs
        if user.is_authenticated:
            return qs.filter(Q(published=True) | Q(author=user))
        return qs.filter(published=True)

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return RecipeWriteSerializer
        if self.action == "retrieve":
            return RecipeDetailSerializer
        return RecipeListSerializer

    def get_permissions(self):
        # DRF folds any `permission_classes` declared on an @action into
        # self.permission_classes, so only apply the viewset defaults when the
        # action did not declare its own.
        if self.action in self._actions_with_permissions():
            return super().get_permissions()
        if self.action == "create":
            permission_classes = [CanCreateRecipe]
        elif self.action in ["update", "partial_update", "destroy"]:
            permission_classes = [IsAuthorOrModeratorOrReadOnly]
        else:
            permission_classes = [permissions.IsAuthenticatedOrReadOnly]
        return [permission() for permission in permission_classes]

    @classmethod
    def _actions_with_permissions(cls):
        return {
            action.__name__ for action in cls.get_extra_actions()
            if "permission_classes" in action.kwargs
        }

    def perform_create(self, serializer):
        # The write serializer takes the author from the request context.
        serializer.save()

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def my_recipes(self, request, pk=None):
        # `request` here is the plain Django request, whose `.user` is only
        # populated for session auth. Use the DRF request for token auth.
        user = self.request.user
        qs = self.filter_queryset(self.get_queryset().filter(author=user))
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=["get"])
    def related(self, request, pk=None):
        recipe = self.get_object()
        serializer = RecipeListSerializer(
            self.get_related_recipes(recipe), many=True, context={"request": request}
        )
        return Response(serializer.data)

    def get_related_recipes(self, recipe):
        qs = Recipe.objects.select_related("author", "category").filter(published=True)
        qs = qs.exclude(pk=recipe.pk)
        if recipe.category_id:
            qs = qs.filter(category_id=recipe.category_id)
        else:
            qs = qs.filter(cuisine=recipe.cuisine) if recipe.cuisine else qs.none()
        return qs.order_by("-created_at")[:4]


class FavoriteViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin):
    """List, create (idempotent) and delete the requesting user's favorites."""

    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = RecipePagination

    def get_queryset(self):
        return Favorite.objects.select_related(
            "recipe", "recipe__author", "recipe__category"
        ).filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return FavoriteCreateSerializer
        return FavoriteSerializer

    def create(self, request, *args, **kwargs):
        serializer = FavoriteCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        favorite = serializer.save()
        payload = FavoriteSerializer(favorite, context={"request": request}).data
        return Response(payload, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        favorite = self.get_object()
        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        Token.objects.create(user=user)


class CustomAuthTokenSerializer(drf_serializers.Serializer):
    username = drf_serializers.CharField()
    password = drf_serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs["username"], password=attrs["password"])
        if not user:
            raise drf_serializers.ValidationError("Invalid credentials.")
        if not user.is_active:
            raise drf_serializers.ValidationError("This account is inactive.")
        token, created = Token.objects.get_or_create(user=user)
        attrs["token"] = token.key
        attrs["user"] = user
        return attrs


class LoginView(ObtainAuthToken):
    serializer_class = CustomAuthTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response({
            "token": serializer.validated_data["token"],
            "user": UserSerializer(serializer.validated_data["user"]).data,
        })


class LogoutView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        Token.objects.filter(user=request.user).delete()
        return Response({"detail": "Successfully logged out."})


class CurrentUserView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
