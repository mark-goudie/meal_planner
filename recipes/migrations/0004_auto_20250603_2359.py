from django.db import migrations

def create_default_tags(apps, schema_editor):
    Tag = apps.get_model('recipes', 'Tag')
    default_tags = [
        "Vegetarian", "Vegan", "Gluten-Free", "Dairy-Free",
        "Quick", "One-Pot", "Make Ahead", "Freezer-Friendly",
        "Kid-Friendly", "Family Favourite", "Dinner Party", "Weeknight Dinner"
    ]
    for name in default_tags:
        Tag.objects.get_or_create(name=name)

class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0003_tag_recipe_tags'),
    ]

    operations = [
        migrations.RunPython(create_default_tags),
    ]
