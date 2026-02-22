# Theming (Energy USA web app)

The Django+Dash app uses a **retro gas-station** look with two themes: **day** (bright, white background) and **night** (warm early-evening dark). Theming is implemented with **plain CSS and custom properties** (variables).

## How it works

- **CSS variables** are defined in `web/static/css/themes.css`:
  - `:root` and `[data-theme="day"]`: `--color-bg`, `--color-accent-red`, `--color-accent-teal`, `--radius-base`, etc.
  - `[data-theme="night"]`: same variables with dark/warm values.
- The **theme switcher** (Day/Night buttons in the header) sets `data-theme` on `<html>` and persists the choice in `localStorage` (key: `energy-usa-theme`). Script: `web/static/js/theme-switcher.js`.
- All layout and components use these variables so switching the theme updates the whole page without duplicating rules.

## Adding other styling tech later

The app does **not** currently use Tailwind, Bootstrap, or another framework. You can add them later without rewriting the theme:

1. **Tailwind**
   - Add Tailwind (e.g. `npm install -D tailwindcss` or use the Tailwind CDN).
   - Keep the existing CSS variables. In Tailwind, reference them where needed, e.g. `bg-[var(--color-bg)]`, `text-[var(--color-accent-teal)]`, or define Tailwind theme extensions that use the same variables so utility classes stay consistent with day/night.

2. **Bootstrap**
   - Add Bootstrap (CDN or build). Prefer using it for **layout/grid** and **components** that don’t override the retro look.
   - Override Bootstrap’s default colors with the same CSS variables (e.g. set `--bs-body-bg: var(--color-bg);` in `[data-theme="day"]` and `[data-theme="night"]`) so Bootstrap components pick up the theme.

3. **Custom CSS**
   - Continue adding rules in `themes.css` (or split into `themes-day.css` / `themes-night.css` if you prefer). Keep using the same variable names so the switcher still controls everything.

No build step is required for the current setup; the day/night themes work with static CSS and the existing script.
