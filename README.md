# Meal Planner

A modern, full-featured Django web application for planning meals, managing recipes, generating shopping lists, and leveraging AI to create new recipes. Designed for individuals and families who want to organize their meals, streamline shopping, and discover new dishes with ease.

---

## Features

- **Recipe Management:**  
  Create, edit, view, and organize your recipes with tags, notes, and AI-generated suggestions.

- **Meal Planning:**  
  Plan meals for any date, with support for breakfast, lunch, and dinner. View your meal plan in a clean, calendar-style interface.

- **Shopping List Generator:**  
  Instantly generate a shopping list from selected recipes or meal plans. Check off items as you shop, print, or export your list.

- **AI Recipe Generator:**  
  Use OpenAI to generate new recipes based on ingredients or ideas you provide.

- **Favorites & Ratings:**  
  Mark recipes as favorites and rate them for quick access to your top dishes.

- **User Authentication:**  
  Secure login, logout, and user-specific data management.

- **Mobile-Friendly & Accessible:**  
  Responsive design and accessibility best practices for all devices.

---

## Getting Started

### Prerequisites

- Python 3.10+
- Django 4.2+ (or 5.x)
- Node.js & npm (for static asset management, optional)
- OpenAI API key (for AI features)

### Installation

1. **Clone the repository:**

   ```sh
   git clone https://github.com/mgoudie/meal_planner.git
   cd meal_planner
   ```

2. **Install dependencies:**

   ```sh
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**

   - Copy `.env.example` to `.env` and set your `OPENAI_API_KEY` and Django `SECRET_KEY`.

4. **Apply migrations:**

   ```sh
   python manage.py migrate
   ```

5. **Create a superuser (optional):**

   ```sh
   python manage.py createsuperuser
   ```

6. **Collect static files:**

   ```sh
   python manage.py collectstatic
   ```

7. **Run the development server:**

   ```sh
   python manage.py runserver
   ```

8. **Access the app:**  
   Visit [http://localhost:8000/](http://localhost:8000/) in your browser.

---

## Running Tests

To run the unit and integration tests:

```sh
python manage.py test
```

---

## Project Structure

```
meal_planner/
├── config/                # Django project settings
├── recipes/               # Main app: models, views, templates, static files
│   ├── templates/
│   │   └── recipes/
│   ├── static/
│   │   └── recipes/
│   ├── templatetags/
│   └── tests/
├── static/                # Project-wide static files
├── templates/registration # Auth templates (login, logout, etc.)
├── requirements.txt
└── manage.py
```

---

## Key Technologies

- **Django**: Web framework
- **Bootstrap 5**: Responsive UI
- **OpenAI API**: AI recipe generation
- **PostgreSQL** (recommended): Database
- **Widget Tweaks**: Enhanced form rendering

---

## Customization & Extensibility

- **Add new features**: See `ProjectNotes.md` for a roadmap and ideas.
- **Theming**: Easily adjust color palette in `main.css`.
- **API Integration**: Extend with REST API or third-party services.

---

## Contributing

Pull requests and suggestions are welcome!  
Please open an issue or discussion for major changes.

---

## License

MIT License

---

## Acknowledgements

- [Bootstrap](https://getbootstrap.com/)
- [OpenAI](https://openai.com/)
- [HeroPatterns](https://heropatterns.com/) for subtle SVG backgrounds

---

## Roadmap & Ideas

See [ProjectNotes.md](./ProjectNotes.md) for planned features and enhancements.

---

**Enjoy planning your meals!**
