import json

from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Category, Recipe, Ingredient, Instruction, Favorite
from .roles import ROLE_COOK, ROLE_LABELS, can_edit_recipe, get_role

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    role_label = serializers.SerializerMethodField()
    is_staff = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "date_joined",
            "role", "role_label", "is_staff",
        ]

    def get_role(self, obj):
        return get_role(obj)

    def get_role_label(self, obj):
        return ROLE_LABELS.get(get_role(obj), ROLE_LABELS[ROLE_COOK])


class FavoriteStateMixin:
    """Favourite state for a recipe, resolved from the prefetch cache.

    Subclasses must declare ``is_favorited`` and ``favorite_id`` as
    ``SerializerMethodField``\\ s; DRF's metaclass only collects declared
    fields from ``Serializer`` subclasses, not from plain mixins.
    """

    def _favorite_for_user(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None
        cache = getattr(obj, "_prefetched_objects_cache", {})
        if "favorited_by" in cache:
            for favorite in cache["favorited_by"]:
                if favorite.user_id == user.pk:
                    return favorite
            return None
        return obj.favorited_by.filter(user=user).first()

    def get_is_favorited(self, obj):
        return self._favorite_for_user(obj) is not None

    def get_favorite_id(self, obj):
        favorite = self._favorite_for_user(obj)
        return favorite.id if favorite else None

    def get_favorited_count(self, obj):
        cache = getattr(obj, "_prefetched_objects_cache", {})
        if "favorited_by" in cache:
            return len(cache["favorited_by"])
        return obj.favorited_by.count()


class RegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "confirm_password"]
        extra_kwargs = {"password": {"write_only": True}}

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs):
        if attrs.get("password") != attrs.get("confirm_password"):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        if len(attrs["password"]) < 8:
            raise serializers.ValidationError({"password": "Password must be at least 8 characters."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        validated_data["email"] = validated_data.get("email", "").strip().lower()
        return User.objects.create_user(**validated_data)


class CategorySerializer(serializers.ModelSerializer):
    recipe_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "description", "image", "recipe_count"]


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ["id", "name", "quantity", "unit", "optional"]


class JSONListField(serializers.ListField):
    """A list field that also accepts repeated JSON-string values.

    Multipart forms cannot carry nested arrays, so the frontend sends one
    JSON string per child row (``ingredients={"name": ...}&ingredients=...``).
    A single JSON array string is accepted too.
    """

    def get_value(self, dictionary):
        # `ListField.get_value` only sees the last value of a QueryDict, so
        # collect every value for the field first.
        if hasattr(dictionary, "getlist"):
            values = dictionary.getlist(self.field_name)
            if len(values) > 1:
                return values
            if len(values) == 1:
                return values[0]
        return dictionary.get(self.field_name, serializers.empty)

    def to_internal_value(self, data):
        if isinstance(data, (str, bytes)):
            try:
                data = json.loads(data)
            except (TypeError, ValueError):
                raise serializers.ValidationError("Expected a JSON list.")
        if not isinstance(data, (list, tuple)):
            raise serializers.ValidationError("Expected a JSON list.")

        decoded = []
        for item in data:
            if isinstance(item, (str, bytes)):
                try:
                    item = json.loads(item)
                except (TypeError, ValueError):
                    raise serializers.ValidationError("Expected a JSON object per item.")
            decoded.append(item)
        return super().to_internal_value(decoded)


class InstructionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instruction
        fields = ["id", "step_number", "description"]
        extra_kwargs = {"step_number": {"required": False}}


class RecipeListSerializer(FavoriteStateMixin, serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    image = serializers.ImageField(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    favorite_id = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            "id", "title", "description", "author", "category", "cuisine",
            "preparation_time", "cooking_time", "servings", "difficulty",
            "image", "created_at", "published", "is_favorited", "favorite_id",
        ]


class RecipeDetailSerializer(FavoriteStateMixin, serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    ingredients = IngredientSerializer(many=True, read_only=True)
    instructions = InstructionSerializer(many=True, read_only=True)
    image = serializers.ImageField(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    favorite_id = serializers.SerializerMethodField()
    favorited_count = serializers.SerializerMethodField()
    related_recipes = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = [
            "id", "title", "description", "author", "category", "cuisine",
            "preparation_time", "cooking_time", "servings", "difficulty",
            "image", "created_at", "updated_at", "published",
            "ingredients", "instructions", "is_favorited", "favorite_id", "favorited_count",
            "related_recipes", "is_owner", "can_edit",
        ]

    def get_is_owner(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and obj.author_id == user.pk)

    def get_can_edit(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return can_edit_recipe(user, obj)

    def get_related_recipes(self, obj):
        request = self.context.get("request")
        qs = Recipe.objects.select_related("author", "category").filter(published=True).exclude(pk=obj.pk)
        if obj.category_id:
            qs = qs.filter(category_id=obj.category_id)
        elif obj.cuisine:
            qs = qs.filter(cuisine=obj.cuisine)
        else:
            qs = qs.none()
        return RecipeListSerializer(
            qs.order_by("-created_at")[:4], many=True, context=self.context
        ).data


class RecipeWriteSerializer(serializers.ModelSerializer):
    ingredients = JSONListField(child=IngredientSerializer(), required=False, write_only=True)
    instructions = JSONListField(child=InstructionSerializer(), required=False, write_only=True)

    class Meta:
        model = Recipe
        fields = [
            "id", "title", "description", "category", "cuisine",
            "preparation_time", "cooking_time", "servings", "difficulty",
            "image", "published", "ingredients", "instructions",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if self.instance is None:
            errors = {}
            if not attrs.get("ingredients"):
                errors["ingredients"] = ["Add at least one ingredient."]
            if not attrs.get("instructions"):
                errors["instructions"] = ["Add at least one preparation step."]
            if errors:
                raise serializers.ValidationError(errors)
        return attrs

    def create(self, validated_data):
        ingredients_data = validated_data.pop("ingredients", [])
        instructions_data = validated_data.pop("instructions", [])
        validated_data.pop("author", None)
        recipe = Recipe.objects.create(author=self.context["request"].user, **validated_data)
        self._replace_children(recipe, ingredients_data, instructions_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop("ingredients", None)
        instructions_data = validated_data.pop("instructions", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        if ingredients_data is not None or instructions_data is not None:
            self._replace_children(
                instance,
                ingredients_data if ingredients_data is not None else [],
                instructions_data if instructions_data is not None else [],
                replace_ingredients=ingredients_data is not None,
                replace_instructions=instructions_data is not None,
            )
        return instance

    def _replace_children(
        self, recipe, ingredients_data, instructions_data,
        replace_ingredients=True, replace_instructions=True,
    ):
        if replace_ingredients:
            recipe.ingredients.all().delete()
            for index, data in enumerate(ingredients_data, start=1):
                data.pop("id", None)
                Ingredient.objects.create(recipe=recipe, **data)
        if replace_instructions:
            recipe.instructions.all().delete()
            for index, data in enumerate(instructions_data, start=1):
                data.pop("id", None)
                data["step_number"] = index
                Instruction.objects.create(recipe=recipe, **data)


class FavoriteSerializer(serializers.ModelSerializer):
    recipe = RecipeListSerializer(read_only=True)

    class Meta:
        model = Favorite
        fields = ["id", "recipe", "created_at"]


class FavoriteCreateSerializer(serializers.Serializer):
    recipe_id = serializers.PrimaryKeyRelatedField(
        queryset=Recipe.objects.all(), source="recipe", write_only=True
    )

    def validate_recipe_id(self, recipe):
        # Drafts are private, so only their author may favorite them.
        # DRF looks up `validate_<field name>`, which is "recipe_id" here.
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not recipe.published and recipe.author_id != getattr(user, "pk", None):
            raise serializers.ValidationError("Recipe is not available.")
        return recipe

    def create(self, validated_data):
        favorite, _ = Favorite.objects.get_or_create(
            user=self.context["request"].user, recipe=validated_data["recipe"]
        )
        return favorite
