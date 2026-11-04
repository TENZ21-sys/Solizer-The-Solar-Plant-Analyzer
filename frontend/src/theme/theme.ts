import { createTheme, type ThemeOptions } from '@mui/material/styles';

// ─── Palette Tokens ──────────────────────────────────────────────────────────
const ACCENT_PRIMARY = '#00BFA6';
const ACCENT_SECONDARY = '#0288D1';
const ACCENT_GRADIENT = 'linear-gradient(135deg, #00BFA6 0%, #0288D1 100%)';

// ─── Shared options ──────────────────────────────────────────────────────────
const sharedTypography = {
  fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  h1: { fontWeight: 700, fontSize: '2.25rem', lineHeight: 1.2, letterSpacing: '-0.02em' },
  h2: { fontWeight: 700, fontSize: '1.875rem', lineHeight: 1.25, letterSpacing: '-0.015em' },
  h3: { fontWeight: 600, fontSize: '1.5rem', lineHeight: 1.3, letterSpacing: '-0.01em' },
  h4: { fontWeight: 600, fontSize: '1.25rem', lineHeight: 1.35 },
  h5: { fontWeight: 600, fontSize: '1.1rem', lineHeight: 1.4 },
  h6: { fontWeight: 600, fontSize: '1rem', lineHeight: 1.4 },
  subtitle1: { fontWeight: 500, fontSize: '0.95rem', lineHeight: 1.5 },
  subtitle2: { fontWeight: 500, fontSize: '0.85rem', lineHeight: 1.5 },
  body1: { fontWeight: 400, fontSize: '0.938rem', lineHeight: 1.6 },
  body2: { fontWeight: 400, fontSize: '0.85rem', lineHeight: 1.6 },
  caption: { fontWeight: 400, fontSize: '0.75rem', lineHeight: 1.5 },
  overline: { fontWeight: 600, fontSize: '0.7rem', lineHeight: 2, letterSpacing: '0.08em' },
  button: { fontWeight: 600, fontSize: '0.875rem', textTransform: 'none' as const, letterSpacing: '0.01em' },
};

const sharedShape = { borderRadius: 12 };

// ─── Light Theme ─────────────────────────────────────────────────────────────
const lightOptions: ThemeOptions = {
  palette: {
    mode: 'light',
    primary: { main: ACCENT_PRIMARY, light: '#4DD0B8', dark: '#00997F', contrastText: '#ffffff' },
    secondary: { main: ACCENT_SECONDARY, light: '#03A9F4', dark: '#01579B' },
    background: { default: '#F5F7FA', paper: '#FFFFFF' },
    text: { primary: '#1A1D2E', secondary: '#5A6178' },
    divider: 'rgba(0,0,0,0.08)',
    error: { main: '#EF5350' },
    warning: { main: '#FF9800' },
    success: { main: '#4CAF50' },
    info: { main: '#2196F3' },
  },
  typography: sharedTypography,
  shape: sharedShape,
  shadows: [
    'none',
    '0px 1px 3px rgba(0,0,0,0.04), 0px 1px 2px rgba(0,0,0,0.06)',
    '0px 2px 6px rgba(0,0,0,0.06), 0px 1px 3px rgba(0,0,0,0.08)',
    '0px 4px 12px rgba(0,0,0,0.06), 0px 2px 4px rgba(0,0,0,0.04)',
    '0px 6px 16px rgba(0,0,0,0.08), 0px 3px 6px rgba(0,0,0,0.05)',
    '0px 8px 24px rgba(0,0,0,0.08), 0px 4px 8px rgba(0,0,0,0.04)',
    '0px 12px 32px rgba(0,0,0,0.10), 0px 6px 12px rgba(0,0,0,0.05)',
    '0px 16px 40px rgba(0,0,0,0.10), 0px 8px 16px rgba(0,0,0,0.05)',
    '0px 20px 48px rgba(0,0,0,0.10)',
    '0px 24px 56px rgba(0,0,0,0.12)',
    '0px 28px 64px rgba(0,0,0,0.12)',
    '0px 32px 72px rgba(0,0,0,0.14)',
    '0px 36px 80px rgba(0,0,0,0.14)',
    '0px 40px 88px rgba(0,0,0,0.16)',
    '0px 44px 96px rgba(0,0,0,0.16)',
    '0px 48px 104px rgba(0,0,0,0.18)',
    '0px 52px 112px rgba(0,0,0,0.18)',
    '0px 56px 120px rgba(0,0,0,0.20)',
    '0px 60px 128px rgba(0,0,0,0.20)',
    '0px 64px 136px rgba(0,0,0,0.22)',
    '0px 68px 144px rgba(0,0,0,0.22)',
    '0px 72px 152px rgba(0,0,0,0.24)',
    '0px 76px 160px rgba(0,0,0,0.24)',
    '0px 80px 168px rgba(0,0,0,0.26)',
    '0px 84px 176px rgba(0,0,0,0.26)',
  ],
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundImage: 'linear-gradient(135deg, #F5F7FA 0%, #E8ECF2 100%)',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          border: '1px solid rgba(0,0,0,0.06)',
          boxShadow: '0px 4px 12px rgba(0,0,0,0.06), 0px 2px 4px rgba(0,0,0,0.04)',
          transition: 'box-shadow 0.3s ease, transform 0.3s ease',
          '&:hover': {
            boxShadow: '0px 8px 24px rgba(0,0,0,0.10), 0px 4px 8px rgba(0,0,0,0.06)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          backgroundImage: 'none',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: 'rgba(255,255,255,0.85)',
          backdropFilter: 'blur(20px)',
          borderBottom: '1px solid rgba(0,0,0,0.06)',
          boxShadow: '0px 1px 3px rgba(0,0,0,0.04)',
          color: '#1A1D2E',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: ({ ownerState }: { ownerState: any }) => ({
          borderRadius: 10,
          padding: '8px 20px',
          fontWeight: 600,
          boxShadow: 'none',
          '&:hover': { boxShadow: 'none' },
          ...(ownerState.variant === 'contained' && ownerState.color === 'primary' && {
            backgroundImage: ACCENT_GRADIENT,
            color: '#fff',
            '&:hover': {
              backgroundImage: ACCENT_GRADIENT,
              filter: 'brightness(1.1)',
            },
          }),
        }),
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { borderRadius: 8, fontWeight: 500 },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: { borderRadius: 8, fontSize: '0.75rem', fontWeight: 500 },
      },
    },
  },
};

// ─── Dark Theme ──────────────────────────────────────────────────────────────
const darkOptions: ThemeOptions = {
  palette: {
    mode: 'dark',
    primary: { main: ACCENT_PRIMARY, light: '#4DD0B8', dark: '#00997F', contrastText: '#ffffff' },
    secondary: { main: ACCENT_SECONDARY, light: '#03A9F4', dark: '#01579B' },
    background: { default: '#0F1219', paper: '#161B26' },
    text: { primary: '#E8ECF2', secondary: '#8B95A8' },
    divider: 'rgba(255,255,255,0.06)',
    error: { main: '#EF5350' },
    warning: { main: '#FFA726' },
    success: { main: '#66BB6A' },
    info: { main: '#42A5F5' },
  },
  typography: sharedTypography,
  shape: sharedShape,
  shadows: [
    'none',
    '0px 1px 3px rgba(0,0,0,0.20), 0px 1px 2px rgba(0,0,0,0.24)',
    '0px 2px 6px rgba(0,0,0,0.22), 0px 1px 3px rgba(0,0,0,0.26)',
    '0px 4px 12px rgba(0,0,0,0.24), 0px 2px 4px rgba(0,0,0,0.20)',
    '0px 6px 16px rgba(0,0,0,0.26), 0px 3px 6px rgba(0,0,0,0.22)',
    '0px 8px 24px rgba(0,0,0,0.28), 0px 4px 8px rgba(0,0,0,0.24)',
    '0px 12px 32px rgba(0,0,0,0.30)',
    '0px 16px 40px rgba(0,0,0,0.30)',
    '0px 20px 48px rgba(0,0,0,0.30)',
    '0px 24px 56px rgba(0,0,0,0.32)',
    '0px 28px 64px rgba(0,0,0,0.32)',
    '0px 32px 72px rgba(0,0,0,0.34)',
    '0px 36px 80px rgba(0,0,0,0.34)',
    '0px 40px 88px rgba(0,0,0,0.36)',
    '0px 44px 96px rgba(0,0,0,0.36)',
    '0px 48px 104px rgba(0,0,0,0.38)',
    '0px 52px 112px rgba(0,0,0,0.38)',
    '0px 56px 120px rgba(0,0,0,0.40)',
    '0px 60px 128px rgba(0,0,0,0.40)',
    '0px 64px 136px rgba(0,0,0,0.42)',
    '0px 68px 144px rgba(0,0,0,0.42)',
    '0px 72px 152px rgba(0,0,0,0.44)',
    '0px 76px 160px rgba(0,0,0,0.44)',
    '0px 80px 168px rgba(0,0,0,0.46)',
    '0px 84px 176px rgba(0,0,0,0.46)',
  ],
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundImage: 'linear-gradient(135deg, #0F1219 0%, #0D1117 100%)',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          border: '1px solid rgba(255,255,255,0.06)',
          background: 'rgba(22, 27, 38, 0.7)',
          backdropFilter: 'blur(24px)',
          boxShadow: '0px 4px 24px rgba(0,0,0,0.3), inset 0px 1px 0px rgba(255,255,255,0.04)',
          transition: 'box-shadow 0.3s ease, transform 0.3s ease, border-color 0.3s ease',
          '&:hover': {
            boxShadow: '0px 8px 32px rgba(0,0,0,0.4), inset 0px 1px 0px rgba(255,255,255,0.06)',
            borderColor: 'rgba(255,255,255,0.10)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          backgroundImage: 'none',
          background: 'rgba(22, 27, 38, 0.6)',
          backdropFilter: 'blur(20px)',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: 'rgba(15, 18, 25, 0.80)',
          backdropFilter: 'blur(20px)',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          boxShadow: '0px 1px 3px rgba(0,0,0,0.30)',
          color: '#E8ECF2',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: ({ ownerState }: { ownerState: any }) => ({
          borderRadius: 10,
          padding: '8px 20px',
          fontWeight: 600,
          boxShadow: 'none',
          '&:hover': { boxShadow: 'none' },
          ...(ownerState.variant === 'contained' && ownerState.color === 'primary' && {
            backgroundImage: ACCENT_GRADIENT,
            color: '#fff',
            '&:hover': {
              backgroundImage: ACCENT_GRADIENT,
              filter: 'brightness(1.15)',
            },
          }),
        }),
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { borderRadius: 8, fontWeight: 500 },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: { borderRadius: 8, fontSize: '0.75rem', fontWeight: 500, backdropFilter: 'blur(8px)' },
      },
    },
  },
};

export const lightTheme = createTheme(lightOptions);
export const darkTheme = createTheme(darkOptions);
export { ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_GRADIENT };
