# Data Integration Platform - Frontend

A modern, production-ready frontend for a data integration platform built with Next.js 14, designed to compete with industry leaders like Fivetran, Matillion, and Airbyte.

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui (Radix UI primitives)
- **State Management**:
  - TanStack Query (React Query) for server state
  - Zustand for client state
- **Forms**: React Hook Form + Zod validation
- **Visualization**: React Flow (lineage), Recharts (metrics)
- **HTTP Client**: Axios
- **Date Handling**: date-fns
- **Notifications**: react-hot-toast
- **Animations**: Framer Motion
- **Theme**: next-themes (dark mode support)

## Features

### Implemented (MVP)
- ✅ Authentication (Login/Register)
- ✅ Dashboard overview with KPIs
- ✅ Pipeline management (CRUD operations)
- ✅ Pipeline creation wizard (5-step guided flow)
- ✅ Source management
- ✅ Destination management
- ✅ Run monitoring with real-time updates
- ✅ Dark mode support
- ✅ Responsive design
- ✅ API client with auth interceptors

### Coming Soon (Phase 2)
- 🔄 Interactive data lineage visualization (React Flow)
- 🔄 Advanced filters and search
- 🔄 Streaming logs viewer
- 🔄 Command palette (Cmd+K)
- 🔄 Onboarding tour
- 🔄 Enhanced error states

## Installation

### Prerequisites

Make sure you have the following installed:
- Node.js 18+ ([Download here](https://nodejs.org/))
- npm or yarn

### Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd /Users/ahmedoladapo/Desktop/data-platform/frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Set up environment variables**:
   The `.env.local` file is already created with:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```
   Update this if your backend runs on a different URL.

4. **Run the development server**:
   ```bash
   npm run dev
   ```

5. **Open your browser**:
   Navigate to [http://localhost:3000](http://localhost:3000)

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking

## Project Structure

```
frontend/
├── app/
│   ├── (auth)/              # Authentication pages (login, register)
│   ├── (dashboard)/         # Protected dashboard pages
│   │   ├── overview/        # Home dashboard
│   │   ├── pipelines/       # Pipeline management
│   │   ├── sources/         # Data sources
│   │   ├── destinations/    # Data destinations
│   │   ├── runs/           # Pipeline runs
│   │   ├── lineage/        # Data lineage
│   │   └── settings/       # User settings
│   ├── layout.tsx          # Root layout
│   ├── page.tsx            # Landing page
│   └── globals.css         # Global styles
│
├── components/
│   ├── ui/                 # shadcn/ui components
│   ├── layout/             # Layout components (Sidebar, Header)
│   └── pipeline/           # Domain-specific components
│
├── lib/
│   ├── api-client.ts       # Axios instance with interceptors
│   └── utils.ts            # Utility functions
│
├── hooks/
│   └── queries/            # TanStack Query hooks
│       ├── useAuth.ts
│       ├── usePipelines.ts
│       ├── useSources.ts
│       └── useDestinations.ts
│
├── types/
│   ├── auth.ts             # Auth type definitions
│   └── pipeline.ts         # Pipeline type definitions
│
└── config/                 # Configuration files

```

## Key Features Explained

### Authentication Flow
- JWT-based authentication with automatic token refresh
- Protected routes using Next.js middleware
- Persistent sessions via localStorage
- Automatic redirect on 401 errors

### State Management Strategy

**TanStack Query (Server State)**:
- Auto-refetch every 30s for pipeline lists
- Polling every 5s for active runs
- Optimistic updates for mutations
- Automatic cache invalidation

**Zustand (Client State)** (to be implemented):
- UI state (sidebar, theme, modals)
- Filter state
- In-app notifications

### Pipeline Creation Wizard
A progressive 5-step wizard:
1. **Basic Info** - Name and description
2. **Source** - Select data source
3. **Destination** - Select destination
4. **Schedule** - Configure cron schedule (optional)
5. **Review** - Review and create

### Real-time Updates
- TanStack Query automatic refetching
- WebSocket/SSE support (planned)
- Live status indicators for running pipelines

### Dark Mode
- System preference detection
- Manual toggle
- Persistent user preference
- CSS variables for theming

## API Integration

The frontend communicates with the backend API at `http://localhost:8000`. Key endpoints:

### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `GET /auth/me` - Get current user

### Pipelines
- `GET /pipelines` - List all pipelines
- `GET /pipelines/:id` - Get pipeline details
- `POST /pipelines` - Create pipeline
- `PUT /pipelines/:id` - Update pipeline
- `DELETE /pipelines/:id` - Delete pipeline
- `POST /pipelines/:id/trigger` - Trigger pipeline run

### Sources & Destinations
- `GET /sources` - List sources
- `POST /sources` - Create source
- `DELETE /sources/:id` - Delete source
- `GET /destinations` - List destinations
- `POST /destinations` - Create destination
- `DELETE /destinations/:id` - Delete destination

### Runs
- `GET /runs` - List all runs
- `GET /runs?pipeline_id=:id` - List runs for specific pipeline

## Design System

### Color Palette
The platform uses a carefully designed color system optimized for data visualization and WCAG AA compliance:

- **Success**: `hsl(142 76% 36%)` - Completed operations
- **Warning**: `hsl(38 92% 50%)` - Warnings and pending states
- **Error**: `hsl(0 84% 60%)` - Failed operations
- **Info**: `hsl(217 91% 60%)` - Informational states
- **Running**: `hsl(262 83% 58%)` - Active pipeline runs

### Typography
- **UI Font**: Inter (sans-serif)
- **Code Font**: JetBrains Mono (planned for logs)

### Spacing
- Consistent spacing scale: 2, 4, 6, 8 (4px increments)
- Sidebar: 256px (16rem)
- Max content width: 1280px

## Progressive Enhancement for User Types

The platform serves two distinct audiences:

### Technical Users (Data Engineers)
- Full access to all features
- Advanced configuration options
- Raw JSON/YAML editors (planned)
- Cron expression input
- Detailed error messages

### Non-Technical Users (SME Business Users)
- Simplified UI with progressive disclosure
- Visual pickers instead of text input
- Plain language error messages
- Guided wizards with helpful tooltips
- Pre-configured templates (planned)

## Performance Optimizations

- Server-side rendering with Next.js 14
- Automatic code splitting
- Image optimization
- Route prefetching
- React Query caching strategy
- Lazy loading of heavy components (planned)

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## Troubleshooting

### Common Issues

**1. API Connection Failed**
- Ensure the backend is running at `http://localhost:8000`
- Check `.env.local` has correct `NEXT_PUBLIC_API_URL`

**2. Authentication Issues**
- Clear localStorage: `localStorage.clear()`
- Check JWT token expiration

**3. Build Errors**
- Clear Next.js cache: `rm -rf .next`
- Reinstall dependencies: `rm -rf node_modules && npm install`

## Development Tips

1. **Hot Reload**: The dev server supports hot module replacement
2. **Type Safety**: Use `npm run type-check` before committing
3. **Linting**: Run `npm run lint -- --fix` to auto-fix issues
4. **Component Development**: Use Storybook (planned) for isolated component development

## Contributing

This is a production-grade frontend. When adding features:

1. Follow existing patterns (hooks, components, types)
2. Use TypeScript strictly (no `any` types without justification)
3. Add proper error handling
4. Implement loading states
5. Ensure responsive design
6. Test on multiple browsers
7. Follow the design system

## Roadmap

### Phase 2 - Enhanced UX (Weeks 5-8)
- [ ] Interactive lineage with React Flow
- [ ] Real-time updates via SSE/WebSocket
- [ ] Advanced filtering and search
- [ ] Log streaming viewer
- [ ] Command palette (Cmd+K)
- [ ] Onboarding tour

### Phase 3 - Advanced Features (Weeks 9-12)
- [ ] Column-level lineage
- [ ] Metrics dashboard with Recharts
- [ ] Pipeline templates
- [ ] Bulk operations
- [ ] Collaboration features
- [ ] Advanced notifications

### Phase 4 - Production Ready (Week 13+)
- [ ] E2E testing with Playwright
- [ ] Performance optimization
- [ ] Accessibility audit (WCAG AA)
- [ ] Mobile/PWA support
- [ ] Advanced RBAC
- [ ] Cost tracking

## License

Proprietary - All rights reserved

## Support

For issues or questions, contact the development team.

---

**Built with ❤️ using Next.js 14, TypeScript, and modern web technologies**
