# F1 Predictions Frontend

Complete React + Vite + TypeScript frontend for F1 race predictions.

## Quick Start

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Setup Environment
Create `.env.local` in the `frontend/` folder:
```
VITE_API_URL=http://localhost:8000
```

### 3. Run Development Server
```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

## Project Structure

```
src/
├── pages/              # Page components (route targets)
│   ├── Home.jsx       # Dashboard with oracle card + standings
│   ├── RaceDetail.jsx # Pre/post-quali delta page
│   ├── ModelReport.jsx # Model metrics & accuracy
│   ├── Drivers.jsx    # Driver prophecy profiles
│   └── Archive.jsx    # Season leaderboard
├── components/        # Reusable UI components
│   ├── OracleCard.jsx           # Hero section with next race
│   ├── DeltaShift.jsx           # Pre/post quali comparison
│   ├── Countdown.jsx            # Race countdown timer
│   ├── ConfidenceMeter.jsx      # Alpha blend visualizer
│   ├── WDCStandings.jsx         # Driver championship
│   ├── WCCStandings.jsx         # Constructor championship
│   ├── ModelSnapshot.jsx        # 3-stat metrics display
│   ├── WeekendFeed.jsx          # Timeline of weekend events
│   ├── SeasonLeaderboard.jsx    # Model accuracy ranking
│   └── MissCard.jsx             # Biggest prediction error
├── hooks/             # Custom React hooks
│   ├── useApi.js     # Generic fetch hook
│   └── useCountdown.js # Countdown timer hook
├── constants/         # App constants
│   └── teamColors.js # Team color palette
└── App.jsx           # Router & nav setup
```

## Design System

### Colors
- Background: `#080808`
- Cards: `#111111`
- Border: `rgba(255,255,255,0.07)`
- Red Accent: `#E10600`
- Text Primary: `#FFFFFF`
- Text Muted: `#777777`
- Cyan: `#27F4D2`

### Typography
- Display: **Barlow Condensed** 900 weight (Google Fonts)
- Body: **DM Sans** (Google Fonts)
- Border Radius: 4px everywhere

### Team Colors
All 11 F1 teams have official hex colors defined in `src/constants/teamColors.js`.

## Available Pages

### `/` (Home)
- Oracle Card: Next race countdown + predicted P1
- Weekend Feed: Schedule of upcoming predictions
- Delta Shift Preview: Top 5 position changes
- WDC/WCC Standings: Current championship
- Model Snapshot: Key metrics
- Season Leaderboard: Driver predictability scores

### `/race/:round` (Race Detail)
- Side-by-side pre-quali vs post-quali predictions
- Position delta visualization (with arrows)
- Confidence meter showing historical vs qualifying weight
- Top 3 podium predictions
- Model's rationale for the predictions

### `/drivers` (Driver Profiles)
- Searchable driver list (left sidebar)
- Per-driver prediction accuracy
- Circular progress ring of accuracy %
- Best/worst predictions for each driver
- Round-by-round history table
- Color-coded error severity

### `/model` (Model Report)
- Live metrics (NDCG, Top-3 Hit Rate, MAE)
- Alpha blend explainer (historical vs qualifying balance)
- Pipeline status (last run, next scheduled)
- Per-round accuracy timeline
- Biggest miss callout

### `/archive` (Season Archive)
- Full season leaderboard
- Predictability scores for all drivers
- Model's Favourite & Chaos Agent badges

## API Integration

All data comes from `http://localhost:8000` (or `VITE_API_URL`).

### Key Endpoints Used
- `GET /api/predictions/next` → Next race predictions
- `GET /api/predictions/{round}/prequali` → Pre-quali for round
- `GET /api/predictions/{round}/postquali` → Post-quali for round
- `GET /api/standings/drivers` → WDC standings
- `GET /api/standings/constructors` → WCC standings
- `GET /api/calendar` → Race calendar with dates
- `GET /api/metrics` → Model metrics & alpha value
- `GET /api/predictions/history` → All historical predictions (for accuracy calc)

## Build & Deploy

### Build for Production
```bash
npm run build
```
Creates optimized build in `dist/`.

### Deploy to Vercel (Recommended)
```bash
npm i -g vercel
vercel
```

Or connect your GitHub repo directly to Vercel for auto-deploys.

### Deploy to Netlify
```bash
npm i -g netlify-cli
netlify deploy --prod --dir=dist
```

## Development Tips

### Styling
- All components use **Tailwind CSS**
- Custom F1 colors in `tailwind.config.js`
- Dark theme enforced with `bg-[#080808]` base

### Data Fetching
- Use `useApi(url)` hook in all components
- Handles loading/error states automatically
- Returns `{ data, loading, error }`

### Animations
- CSS transitions for smooth UI updates
- SVG circular progress rings for accuracy %
- Skeleton loaders while fetching data

### Performance
- Each page independently fetches its data
- No global state manager needed (kept simple)
- Lazy loaded routes via React Router

## Troubleshooting

**"Cannot fetch from localhost:8000"**
- Ensure backend is running: `python app/main.py`
- Check `.env.local` has correct `VITE_API_URL`
- Backend should have CORS enabled (it does)

**"Tailwind styles not applying"**
- Run `npm install` to get latest tailwindcss
- Restart dev server: `npm run dev`

**"Round predictions not loading"**
- Backend needs to have generated predictions for that round
- Check `/api/predictions/{round}/prequali` returns data
- If 404, run pipeline: POST `/api/refresh` on backend

## Next Steps

- [ ] Add real race results data to compare vs predictions
- [ ] Implement WebSocket for live prediction updates
- [ ] Add user preferences (favorite drivers/teams)
- [ ] Export predictions as CSV/JSON
- [ ] Email alerts for major prediction changes
- [ ] Dark mode toggle (already dark, could add light mode)
- [ ] Mobile responsive design
