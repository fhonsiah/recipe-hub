"""Seed the database with categories, demo users and recipes.

    python manage.py seed_data [--flush]

Idempotent: re-running updates nothing and simply reports the existing counts,
unless ``--flush`` is passed, which deletes recipes, favorites, categories and
the demo users first.
"""
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from api.models import Category, Favorite, Ingredient, Instruction, Recipe
from api.roles import (
    ROLE_ADMIN,
    ROLE_COOK,
    ROLE_LABELS,
    ROLE_MODERATOR,
    assign_role,
    ensure_groups,
    get_role,
)

User = get_user_model()

CATEGORIES = [
    ("Breakfast", "Quick morning meals and slow weekend brunches.", "Brunch"),
    ("Lunch", "Midday dishes that fit into a working day.", "Lunch"),
    ("Dinner", "Weeknight suppers and weekend feasts.", "Dinner"),
    ("Dessert", "Sweet finishes, from custards to cakes.", "Dessert"),
    ("Vegetarian", "Plant-forward mains and sides.", "Veggie"),
    ("Baking", "Bread, pastry and anything that needs an oven.", "Baking"),
    ("Healthy", "Light, balanced and nutrient-dense.", "Healthy"),
    ("Snack", "Small bites, dips and party food.", "Snack"),
]

DEMO_USERS = [
    ("mara", "mara@example.com", "Mara", ROLE_COOK),
    ("tomas", "tomas@example.com", "Tomas", ROLE_COOK),
    ("aiko", "aiko@example.com", "Aiko", ROLE_COOK),
    ("sam", "sam@example.com", "Sam", ROLE_COOK),
    ("editor", "editor@example.com", "Evan", ROLE_MODERATOR),
    ("chief", "chief@example.com", "Rhea", ROLE_ADMIN),
]

PASSWORD = "recipehub123"

#: Indexes of ``mara``'s recipes that are also seeded as unpublished drafts,
#: so a moderator has something to review on a fresh database.
DRAFT_RECIPE_INDEXES = (3, 9)

RECIPES = [
    {
        "title": "Charred Tomato Basil Pasta",
        "category": "Dinner", "cuisine": "Italian", "difficulty": "easy",
        "preparation_time": 10, "cooking_time": 20, "servings": 4, "author": "mara",
        "description": "Burst cherry tomatoes, plenty of basil and a slick of olive oil turn a handful of pantry staples into a dinner that tastes like summer.",
        "ingredients": [
            ("Spaghetti", 400, "g", False), ("Cherry tomatoes", 400, "g", False),
            ("Garlic cloves", 3, "pieces", False), ("Olive oil", 4, "tbsp", False),
            ("Fresh basil leaves", 1, "handful", True), ("Parmesan", 50, "g", True),
            ("Chilli flakes", 1, "tsp", True), ("Sea salt", 1, "tsp", False),
        ],
        "steps": [
            "Boil the spaghetti in generously salted water until just shy of al dente, about 9 minutes.",
            "Meanwhile, heat a wide pan over high heat and add the olive oil.",
            "Add the tomatoes and cook until they blister and burst, roughly 6 minutes.",
            "Lower the heat, add the sliced garlic and chilli flakes, and cook for 1 minute more.",
            "Drain the pasta, reserving a cup of the cooking water, and add it to the pan.",
            "Toss over a low heat, loosening with pasta water until glossy, then fold through the basil.",
            "Finish with grated parmesan, a drizzle of good olive oil and more chilli flakes.",
        ],
    },
    {
        "title": "Cardamom Banana Oat Breakfast",
        "category": "Breakfast", "cuisine": "American", "difficulty": "easy",
        "preparation_time": 5, "cooking_time": 8, "servings": 2, "author": "aiko",
        "description": "Creamy oats warmed with banana and cardamom, finished with toasted walnuts. Ready before the kettle boils the second time.",
        "ingredients": [
            ("Rolled oats", 100, "g", False), ("Bananas", 2, "pieces", False),
            ("Ground cardamom", 1, "tsp", False), ("Milk", 400, "ml", False),
            ("Walnuts", 50, "g", True), ("Maple syrup", 2, "tbsp", True),
        ],
        "steps": [
            "Toast the oats in a dry pan for 1 minute until they smell nutty.",
            "Add the milk and sliced banana, and bring to a gentle simmer.",
            "Cook for 6 to 8 minutes, stirring often, until the oats are thick and creamy.",
            "Stir through the ground cardamom and maple syrup.",
            "Divide between bowls and top with toasted walnuts and an extra drizzle of syrup.",
        ],
    },
    {
        "title": "Smoky Black Bean Tacos",
        "category": "Vegetarian", "cuisine": "Mexican", "difficulty": "easy",
        "preparation_time": 15, "cooking_time": 15, "servings": 4, "author": "tomas",
        "description": "Chipotle and cumin turn tinned black beans into something far from humble. Twenty minutes from the cupboard to the table.",
        "ingredients": [
            ("Black beans", 800, "g", False), ("Tortillas", 12, "pieces", False),
            ("Chipotle paste", 2, "tbsp", False), ("Ground cumin", 2, "tsp", False),
            ("Red onion", 1, "piece", False), ("Lime", 2, "pieces", False),
            ("Coriander leaves", 1, "handful", True), ("Avocado", 2, "pieces", True),
        ],
        "steps": [
            "Finely dice the red onion and set half of it aside for the topping.",
            "Fry the remaining onion in a little oil until soft, about 4 minutes.",
            "Add the cumin and chipotle paste and fry for 1 minute until fragrant.",
            "Add the drained beans with a splash of water and mash about half of them.",
            "Simmer for 8 minutes, season, and finish with the juice of one lime.",
            "Warm the tortillas in a dry pan, then fill and finish with the reserved onion, avocado and coriander.",
        ],
    },
    {
        "title": "No-Knead Sourdough Focaccia",
        "category": "Baking", "cuisine": "Italian", "difficulty": "hard",
        "preparation_time": 25, "cooking_time": 30, "servings": 8, "author": "mara",
        "description": "A dimpled, olive-oil-heavy focaccia with a crisp base and an almost custardy centre. Most of the work is waiting.",
        "ingredients": [
            ("Strong white bread flour", 500, "g", False), ("Instant yeast", 2, "tsp", False),
            ("Warm water", 400, "ml", False), ("Olive oil", 80, "ml", False),
            ("Fine sea salt", 12, "g", False), ("Rosemary", 4, "tsp", True),
        ],
        "steps": [
            "Whisk the flour, yeast and 10 g of the salt together, then add the water.",
            "Mix until no dry flour remains, cover, and leave for 10 minutes.",
            "Add the remaining salt and 40 ml of olive oil, then stretch and fold the dough four times over 2 hours.",
            "Pour the remaining oil into a 30 x 45 cm pan and ease the dough in to fill the corners.",
            "Proof for 2 hours at room temperature until the dough is visibly bubbly.",
            "Dimple deeply with oiled fingers, scatter the rosemary and salt, and bake at 220 C for 25 to 30 minutes until deep gold.",
        ],
    },
    {
        "title": "Silky Thai Green Curry",
        "category": "Dinner", "cuisine": "Thai", "difficulty": "medium",
        "preparation_time": 20, "cooking_time": 25, "servings": 4, "author": "aiko",
        "description": "Crack the coconut cream, fry the paste until the oil splits, and you get a curry with real depth instead of a jar sauce.",
        "ingredients": [
            ("Coconut milk", 800, "ml", False), ("Green curry paste", 3, "tbsp", False),
            ("Chicken thighs", 700, "g", False), ("Thai basil", 2, "tbsp", True),
            ("Fish sauce", 2, "tbsp", False), ("Palm sugar", 1, "tsp", False),
            ("Red chillies", 2, "pieces", True), ("Rice", 300, "g", False),
        ],
        "steps": [
            "Open the coconut milk without shaking and spoon the thick cream from the top into a hot wok.",
            "Cook the cream for 3 minutes until it splits, then add the curry paste and fry for 2 minutes.",
            "Add the sliced chicken and turn to coat, cooking for 5 minutes.",
            "Pour in the remaining coconut milk, add the fish sauce and palm sugar, and simmer for 12 minutes.",
            "Stir through the Thai basil, remove from the heat, and finish with the sliced chillies.",
            "Serve with steamed rice.",
        ],
    },
    {
        "title": "Classic French Onion Soup",
        "category": "Lunch", "cuisine": "French", "difficulty": "hard",
        "preparation_time": 20, "cooking_time": 70, "servings": 6, "author": "sam",
        "description": "An hour of patient, unattended caramelising buys a broth with real depth. Bread and cheese are non-negotiable.",
        "ingredients": [
            ("Onions", 1500, "g", False), ("Butter", 60, "g", False),
            ("Beef stock", 1200, "ml", False), ("White wine", 200, "ml", False),
            ("Baguette", 1, "piece", False), ("Gruyere", 200, "g", False),
            ("Thyme", 4, "tsp", True), ("Bay leaves", 2, "pieces", True),
        ],
        "steps": [
            "Slice the onions pole to pole. Cooking them any other way gives you soup.",
            "Melt the butter in a heavy casserole and add the onions with a good pinch of salt.",
            "Cook over low heat for 60 to 70 minutes, stirring every 10 minutes, until deeply golden and collapsed.",
            "Pour in the wine and scrape the base clean, then reduce by a third.",
            "Add the stock, thyme and bay, and simmer gently for 20 minutes.",
            "Toast baguette slices, ladle over the soup, cover with gruyere and grill until bubbling.",
        ],
    },
    {
        "title": "Miso Glazed Salmon Bowls",
        "category": "Healthy", "cuisine": "Japanese", "difficulty": "easy",
        "preparation_time": 15, "cooking_time": 12, "servings": 2, "author": "aiko",
        "description": "A weeknight salmon that tastes like a restaurant dish: sweet-savoury glaze, sesame rice, quick-pickled cucumber.",
        "ingredients": [
            ("Salmon fillets", 400, "g", False), ("White miso", 3, "tbsp", False),
            ("Mirin", 2, "tbsp", False), ("Sushi rice", 200, "g", False),
            ("Cucumber", 1, "piece", False), ("Sesame seeds", 2, "tsp", True),
            ("Spring onions", 2, "pieces", True), ("Rice vinegar", 2, "tbsp", False),
        ],
        "steps": [
            "Whisk the miso, mirin and 1 tablespoon of warm water into a smooth glaze.",
            "Brush the salmon thickly with the glaze and leave for 10 minutes.",
            "Meanwhile, cook the rice and pickle the cucumber in the rice vinegar for 10 minutes.",
            "Grill or pan-sear the salmon for 5 to 6 minutes per side until it just flakes.",
            "Spoon the rice into bowls, add the salmon and cucumber, and finish with sesame and spring onion.",
        ],
    },
    {
        "title": "Dark Chocolate Olive Oil Cake",
        "category": "Dessert", "cuisine": "Mediterranean", "difficulty": "medium",
        "preparation_time": 20, "cooking_time": 40, "servings": 10, "author": "sam",
        "description": "No mixer, no butter, barely any sugar. The olive oil makes the crumb stay tender for days.",
        "ingredients": [
            ("Plain flour", 200, "g", False), ("Cocoa powder", 60, "g", False),
            ("Dark chocolate", 200, "g", False), ("Olive oil", 180, "ml", False),
            ("Caster sugar", 250, "g", False), ("Eggs", 3, "pieces", False),
            ("Sea salt", 1, "tsp", False), ("Orange zest", 1, "tbsp", True),
        ],
        "steps": [
            "Melt the chocolate, then whisk in the olive oil while it is still warm.",
            "Whisk the sugar and eggs together until pale and thick.",
            "Fold the chocolate into the eggs, then sift over the flour, cocoa and salt.",
            "Fold until just combined, then pour into a lined 20 cm tin.",
            "Bake at 175 C for 38 to 40 minutes. It should still have a slight wobble in the centre.",
            "Cool completely in the tin before turning out and finishing with orange zest.",
        ],
    },
    {
        "title": "Crunchy Peanut Noodle Salad",
        "category": "Lunch", "cuisine": "Chinese", "difficulty": "easy",
        "preparation_time": 20, "cooking_time": 10, "servings": 4, "author": "tomas",
        "description": "A cold, crunchy, deeply savoury salad that keeps for three days in the fridge and improves overnight.",
        "ingredients": [
            ("Egg noodles", 400, "g", False), ("Peanut butter", 80, "g", False),
            ("Soy sauce", 3, "tbsp", False), ("Rice vinegar", 2, "tbsp", False),
            ("Cucumber", 1, "piece", False), ("Carrots", 2, "pieces", False),
            ("Red cabbage", 200, "g", True), ("Sesame oil", 2, "tsp", True),
            ("Chilli crisp", 3, "tbsp", True),
        ],
        "steps": [
            "Boil the noodles for 4 minutes, then rinse under cold water until completely cool.",
            "Whisk the peanut butter, soy sauce, vinegar and sesame oil with 3 tablespoons of warm water until pourable.",
            "Julienne the cucumber and carrots and finely shred the cabbage.",
            "Toss the noodles, vegetables and dressing together.",
            "Finish with chilli crisp and serve cold, or chill until needed.",
        ],
    },
    {
        "title": "Rosemary Focaccia Doughnuts",
        "category": "Dessert", "cuisine": "American", "difficulty": "hard",
        "preparation_time": 40, "cooking_time": 15, "servings": 12, "author": "mara",
        "description": "A yeasted doughnut that is honestly worth the afternoon it takes. Crisp outside, cloud-soft inside.",
        "ingredients": [
            ("Strong white bread flour", 400, "g", False), ("Instant yeast", 7, "g", False),
            ("Whole milk", 250, "ml", False), ("Caster sugar", 60, "g", False),
            ("Eggs", 2, "pieces", False), ("Butter", 80, "g", False),
            ("Rosemary", 3, "tsp", True), ("Sugar", 100, "g", True),
        ],
        "steps": [
            "Mix the flour, yeast, sugar, milk and eggs into a soft dough and knead for 10 minutes.",
            "Add the butter a knob at a time until fully incorporated, then knead a further 5 minutes.",
            "Proof until doubled, about 90 minutes, then roll to 2 cm thick and rest for 20 minutes.",
            "Cut rounds, proof for another 40 minutes until puffy.",
            "Fry at 180 C for about 90 seconds per side until golden.",
            "Roll in sugar and rosemary while still hot.",
        ],
    },
    {
        "title": "Chickpea Smash Cucumber Bowls",
        "category": "Healthy", "cuisine": "Mediterranean", "difficulty": "easy",
        "preparation_time": 15, "cooking_time": 0, "servings": 2, "author": "tomas",
        "description": "Smashed chickpeas, sharp cucumber, and a tahini dressing. Fifteen minutes, no cooking, endlessly repeatable.",
        "ingredients": [
            ("Chickpeas", 800, "g", False), ("Cucumber", 1, "piece", False),
            ("Tahini", 3, "tbsp", False), ("Lemon", 1, "piece", False),
            ("Garlic cloves", 1, "piece", False), ("Olive oil", 3, "tbsp", False),
            ("Parsley", 1, "handful", True), ("Sumac", 1, "tsp", True),
        ],
        "steps": [
            "Drain the chickpeas well, reserving a little of the liquid, then roughly smash with a fork.",
            "Dice the cucumber and slice the garlic thinly.",
            "Whisk the tahini with the lemon juice, garlic and enough chickpea liquid to make a pourable dressing.",
            "Toss the chickpeas and cucumber with the dressing and olive oil.",
            "Scatter over the parsley and sumac and serve straight away.",
        ],
    },
    {
        "title": "Shakshuka with Feta",
        "category": "Breakfast", "cuisine": "Middle Eastern", "difficulty": "medium",
        "preparation_time": 15, "cooking_time": 35, "servings": 4, "author": "sam",
        "description": "Eggs poached in a spiced tomato and pepper sauce. Equally good for brunch as for a late dinner.",
        "ingredients": [
            ("Eggs", 8, "pieces", False), ("Chopped tomatoes", 800, "g", False),
            ("Red peppers", 2, "pieces", False), ("Onion", 1, "piece", False),
            ("Garlic cloves", 3, "pieces", False), ("Cumin", 2, "tsp", False),
            ("Smoked paprika", 1, "tsp", False), ("Feta", 150, "g", True),
            ("Parsley", 1, "handful", True),
        ],
        "steps": [
            "Soften the sliced onion and peppers in olive oil for 15 minutes.",
            "Add the garlic and spices and fry for 1 minute.",
            "Pour in the tomatoes, season, and simmer for 15 minutes until thick.",
            "Make wells in the sauce and crack in the eggs. Cover and cook for 6 to 8 minutes until the whites set.",
            "Crumble over the feta, scatter with parsley, and serve with bread.",
        ],
    },
]


class Command(BaseCommand):
    help = "Populate the database with demo categories, users and recipes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing recipes, favorites, categories and demo users first.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            Favorite.objects.all().delete()
            Recipe.objects.all().delete()
            Category.objects.all().delete()
            User.objects.filter(
                username__in=[u[0] for u in DEMO_USERS], is_superuser=False
            ).delete()
            self.stdout.write(self.style.WARNING("Flushed existing demo data."))

        categories = {}
        for name, description, cuisine in CATEGORIES:
            category, _ = Category.objects.get_or_create(
                name=name, defaults={"description": description}
            )
            categories[name] = category
        self.stdout.write(self.style.SUCCESS("Categories: %d" % Category.objects.count()))

        users = {}
        for username, email, name, role in DEMO_USERS:
            user, created = User.objects.get_or_create(
                username=username, defaults={"email": email, "first_name": name}
            )
            if created:
                user.set_password(PASSWORD)
                user.first_name = name
                user.email = email
                user.save()
            assign_role(user, role)
            users[username] = user

        self.stdout.write(self.style.SUCCESS("Roles: %s" % ", ".join(ensure_groups())))
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Demo accounts (password: %s)" % PASSWORD))
        for username, email, name, role in DEMO_USERS:
            self.stdout.write("  %-9s %-22s %s" % (username, email, ROLE_LABELS[role]))
        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                "These are throwaway demo credentials. Change or remove them before "
                "deploying anywhere public."
            )
        )

        created_count = 0
        now = timezone.now()
        for index, payload in enumerate(RECIPES):
            title = payload["title"]
            if Recipe.objects.filter(title=title).exists():
                continue

            # Give the moderator a couple of unpublished submissions so the
            # review workflow is demonstrable out of the box.
            if payload["author"] == "mara" and index in DRAFT_RECIPE_INDEXES:
                Recipe.objects.create(
                    title="[Needs review] " + title,
                    description=payload["description"],
                    author=users[payload["author"]],
                    category=categories[payload["category"]],
                    cuisine=payload["cuisine"],
                    preparation_time=payload["preparation_time"],
                    cooking_time=payload["cooking_time"],
                    servings=payload["servings"],
                    difficulty=payload["difficulty"],
                    published=False,
                    created_at=now - timedelta(days=1),
                )
                created_count += 1

            recipe = Recipe.objects.create(
                title=title,
                description=payload["description"],
                author=users[payload["author"]],
                category=categories[payload["category"]],
                cuisine=payload["cuisine"],
                preparation_time=payload["preparation_time"],
                cooking_time=payload["cooking_time"],
                servings=payload["servings"],
                difficulty=payload["difficulty"],
                published=True,
                created_at=now - timedelta(days=len(RECIPES) - index),
            )
            for name, quantity, unit, optional in payload["ingredients"]:
                Ingredient.objects.create(
                    recipe=recipe, name=name, quantity=quantity, unit=unit, optional=optional
                )
            for order, step in enumerate(payload["steps"], start=1):
                Instruction.objects.create(
                    recipe=recipe, step_number=order, description=step
                )
            created_count += 1

        self.stdout.write(self.style.SUCCESS("Recipes created: %d (total %d)" % (created_count, Recipe.objects.count())))

        # A little social proof so the dashboard stats are not all zero.
        # Only cooks favorite recipes; curators are there to moderate, not to
        # generate activity.
        random.seed(42)
        cooks = [u for u in users.values() if get_role(u) == ROLE_COOK]
        for recipe in Recipe.objects.all():
            for user in random.sample(cooks, k=random.randint(0, len(cooks))):
                Favorite.objects.get_or_create(user=user, recipe=recipe)
        self.stdout.write(self.style.SUCCESS("Favorites: %d" % Favorite.objects.count()))
