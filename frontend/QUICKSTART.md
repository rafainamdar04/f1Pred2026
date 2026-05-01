# F1 Predictions Frontend - Quick Start

## 📦 Installation

```bash
cd frontend
npm install
```

This installs:
- `react-router-dom` - Page routing
- `tailwindcss` - Styling framework
- All other dependencies (React, Vite, TypeScript, etc.)

## 🚀 Run Development Server

```bash
npm run dev
```

- Opens on http://localhost:5173
- Hot reload on file changes
- Browser automatically refreshes

## 🎨 Design System at a Glance

### Colors
```js
// Use these anywhere in Tailwind
bg-[#080808]      // Background
bg-[#111111]      // Cards
text-[#FFFFFF]    // Primary text
text-[#777777]    // Muted text
text-[#E10600]    // Red accent
text-[#27F4D2]    // Cyan (positive)
```

### Fonts
```html
<!-- Display (F1 style) -->
<h1 className="font-black font-barlow">text</h1>

<!-- Body (default) -->
<p>regular text</p>
```

### Team Colors
```js
import { TEAM_COLORS } from './constants/teamColors';

TEAM_COLORS['Ferrari']        // '#E8002D'
TEAM_COLORS['Mercedes']       // '#27F4D2'
TEAM_COLORS['McLaren']        // '#FF8000'
```

## 📑 Pages Built

| Route | Component | Purpose |
|-------|-----------|---------|
| `/` | `Home` | Dashboard with all stats |
| `/race/:round` | `RaceDetail` | Pre/post-quali comparison |
| `/drivers` | `Drivers` | Driver accuracy profiles |
| `/model` | `ModelReport` | Model metrics & performance |
| `/archive` | `Archive` | Season leaderboard |

## 🔌 Key Components

### Data Fetching
```js
import { useApi } from '../hooks/useApi';

function MyComponent() {
  const { data, loading, error } = useApi('/api/predictions/next');
  
  if (loading) return <Skeleton />;
  if (error) return <div>Error: {error}</div>;
  
  return <div>{data.race_name}</div>;
}
```

### Countdown Timer
```js
import { Countdown } from './components/Countdown';

<Countdown targetDate="2026-04-28T20:00:00Z" />
```

### Confidence Meter
```js
import { ConfidenceMeter } from './components/ConfidenceMeter';

<ConfidenceMeter alpha={0.65} round={1} />
```

## 🛠️ Environment Setup

Create `.env.local`:
```
VITE_API_URL=http://localhost:8000
```

## 📱 File Modifications Needed

The following files have already been created/updated:

✅ `/src/pages/` - All 5 pages
✅ `/src/components/` - All 8 reusable components  
✅ `/src/hooks/` - useApi + useCountdown
✅ `/src/constants/teamColors.js` - Team color palette
✅ `/src/App.jsx` - React Router setup
✅ `/src/index.css` - Google Fonts + Tailwind
✅ `/tailwind.config.js` - Design tokens
✅ `/postcss.config.js` - Tailwind pipeline
✅ `/package.json` - Dependencies updated

## 🔍 Next: Backend Compatibility

Ensure your backend is returning data in these shapes:

### /api/predictions/next
```json
{
  "round": 1,
  "race_name": "Australian Grand Prix",
  "rows": [
    {
      "driver_id": "alb",
      "constructor_id": "red_bull",
      "final_score": 95.2,
      "rationale": "Strong qualifying pace..."
    }
  ],
  "alpha": 0.65
}
```

### /api/standings/drivers
```json
{
  "drivers": [
    {
      "position": 1,
      "driver_id": "ver",
      "driver_name": "Max Verstappen",
      "constructor_name": "Red Bull Racing",
      "points": 25,
      "wins": 1
    }
  ]
}
```

## ⚡ Build for Production

```bash
npm run build
npm run preview    # Test production build locally
```

Then deploy `dist/` folder to Vercel, Netlify, etc.

## 🐛 Common Issues

| Issue | Solution |
|-------|----------|
| Styles not showing | Restart dev server |
| API 404 errors | Ensure backend running on 8000 |
| Router not working | Check `/src/App.jsx` imports |
| Tailwind not found | Run `npm install` |

---

**Ready to start?** Run `npm install && npm run dev` and open localhost:5173!
