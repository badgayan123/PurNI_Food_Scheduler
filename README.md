# PurNi Menu

Weekly meal planner for **Purnima** & **Nitesh** — editable from any device, with calorie and protein tracking and graphs.

## Features

- **Editable weekly menu** — Both Purnima and Nitesh can add/edit meals
- **Calorie & protein** per food, with auto-lookup from common foods
- **Bar charts** — Calories and protein per day
- **Week navigation** — Browse previous/next weeks
- **Any device** — Works on phone, tablet, laptop

## Run locally

```bash
cd PurNi_Menu
pip install -r requirements.txt
python run.py
```

Open http://localhost:8000

## Deploy (any device access)

### Option 1: Render (recommended)

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect the repo
4. Settings:
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Deploy — you’ll get a URL like `https://purni-menu.onrender.com`

### Option 2: Railway

1. Push to GitHub
2. Go to [railway.app](https://railway.app) → New project → Deploy from GitHub
3. Add a Web Service, connect the repo
4. Railway will detect Python; add start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Deploy and open the public URL

## Optional: USDA nutrition API

For more accurate nutrition data:

1. Get a free API key from [FoodData Central](https://fdc.nal.usda.gov/api-guide.html)
2. Add as env var: `USDA_API_KEY=your_key`

Without it, the app uses a built-in list of common foods (rice, dal, chicken, etc.).
