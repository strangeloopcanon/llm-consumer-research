# Consumer Research Web UI

A modern, responsive web interface for the Synthetic Consumer Research Service.

## Features

- **Multi-Model Support**: Query OpenAI, Anthropic (Claude), Google (Gemini), and Perplexity in a single simulation
- **Real-time Results**: Interactive dashboard with purchase intent metrics and persona breakdowns
- **Beautiful Visualizations**: Charts and stats powered by Recharts
- **Responsive Design**: Works seamlessly on desktop and mobile devices

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- The backend API server running on `http://localhost:8000`
- Optional: set `VITE_API_URL` if your backend is not on `http://localhost:8000`

### Installation

```bash
npm install
```

### Development

Start the development server:

```bash
npm run dev
```

The UI will be available at `http://localhost:5173`

### Production Build

```bash
npm run build
npm run preview  # Preview the production build
```

## Render Deployment

The root repository includes `/render.yaml` with a free-tier Render blueprint:

- backend web service (`llm-consumer-research-api`)
- static frontend (`llm-consumer-research-ui`)

`VITE_API_URL` is wired from the backend Render URL automatically.

## How to Use

1. **Start the Backend**: Make sure the FastAPI backend is running:
   ```bash
   cd ..
   source .venv311/bin/activate
   uvicorn ssr_service.api:app --host 0.0.0.0 --port 8000
   ```

2. **Open the UI**: Navigate to `http://localhost:5173` in your browser

3. **Configure Your Simulation**:
   - Enter your product concept (title, description, price)
   - Select your target audience
   - Choose which LLM providers to query
   - Set your desired sample size

4. **Run**: Click "Run Simulation" and wait for results

5. **Analyze**: Review the aggregate purchase intent, rating distribution, and persona-specific insights

## Architecture

- **React 19** with TypeScript
- **Vite** for blazing-fast builds
- **Tailwind CSS** for styling
- **Recharts** for data visualization
- **Axios** for API communication
- **Lucide React** for icons
