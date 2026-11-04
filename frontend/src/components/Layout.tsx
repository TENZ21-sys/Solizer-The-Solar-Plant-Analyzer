import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Tooltip,
  Badge,
  Divider,
} from '@mui/material';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import NotificationsIcon from '@mui/icons-material/Notifications';
import HomeRoundedIcon from '@mui/icons-material/HomeRounded';
import FactoryRoundedIcon from '@mui/icons-material/FactoryRounded';
import CloudUploadRoundedIcon from '@mui/icons-material/CloudUploadRounded';
import EqualizerRoundedIcon from '@mui/icons-material/EqualizerRounded';
import MemoryRoundedIcon from '@mui/icons-material/MemoryRounded';
import ReportProblemRoundedIcon from '@mui/icons-material/ReportProblemRounded';
import TimelineRoundedIcon from '@mui/icons-material/TimelineRounded';
import WbSunnyRoundedIcon from '@mui/icons-material/WbSunnyRounded';
import DescriptionRoundedIcon from '@mui/icons-material/DescriptionRounded';
import SettingsRoundedIcon from '@mui/icons-material/SettingsRounded';

import { useThemeMode } from '../theme/ThemeContext';
import { usePlant } from '../context/PlantContext';
import { ACCENT_GRADIENT } from '../theme/theme';

const SIDEBAR_WIDTH = 260;
const COLLAPSED_SIDEBAR_WIDTH = 76;

interface NavigationItem {
  name: string;
  path: string;
  icon: React.ReactElement;
}

export const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const { mode, toggleTheme } = useThemeMode();
  const { plants, selectedPlantId, setSelectedPlantId, loading } = usePlant();
  
  const location = useLocation();
  const navigate = useNavigate();

  const menuItems: NavigationItem[] = [
    { name: 'Dashboard', path: '/', icon: <HomeRoundedIcon /> },
    { name: 'Plant Profile', path: '/plant', icon: <FactoryRoundedIcon /> },
    { name: 'Data Import', path: '/import', icon: <CloudUploadRoundedIcon /> },
    { name: 'Performance', path: '/performance', icon: <EqualizerRoundedIcon /> },
    { name: 'Inverters', path: '/inverters', icon: <MemoryRoundedIcon /> },
    { name: 'Loss Analysis', path: '/losses', icon: <ReportProblemRoundedIcon /> },
    { name: 'Degradation', path: '/degradation', icon: <TimelineRoundedIcon /> },
    { name: 'Irradiation', path: '/irradiation', icon: <WbSunnyRoundedIcon /> },
    { name: 'Alerts', path: '/alerts', icon: <Badge color="error" variant="dot"><NotificationsIcon /></Badge> },
    { name: 'Reports', path: '/reports', icon: <DescriptionRoundedIcon /> },
    { name: 'Settings', path: '/settings', icon: <SettingsRoundedIcon /> },
  ];

  const handlePlantChange = (event: any) => {
    const val = event.target.value;
    setSelectedPlantId(val === '' ? null : Number(val));
  };

  const activeSidebarWidth = collapsed ? COLLAPSED_SIDEBAR_WIDTH : SIDEBAR_WIDTH;

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      
      {/* ─── Top AppBar ──────────────────────────────────────────────────────── */}
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          width: `calc(100% - ${activeSidebarWidth}px)`,
          ml: `${activeSidebarWidth}px`,
          borderBottom: '1px solid',
          borderColor: 'divider',
          bgcolor: mode === 'dark' ? 'rgba(15, 18, 25, 0.75)' : 'rgba(255, 255, 255, 0.75)',
          backdropFilter: 'blur(12px)',
          transition: (theme) => theme.transitions.create(['width', 'margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.enteringScreen,
          }),
          zIndex: (theme) => theme.zIndex.drawer + 1,
        }}
      >
        <Toolbar sx={{ justifyContent: 'space-between', px: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {/* Plant Selector */}
            <FormControl size="small" sx={{ minWidth: 200 }}>
              <InputLabel id="plant-select-label">Active Power Plant</InputLabel>
              <Select
                labelId="plant-select-label"
                id="plant-select"
                value={selectedPlantId ?? ''}
                label="Active Power Plant"
                onChange={handlePlantChange}
                disabled={loading || plants.length === 0}
                sx={{
                  borderRadius: 2,
                  '& .MuiOutlinedInput-notchedOutline': {
                    borderColor: 'divider',
                  },
                }}
              >
                {plants.map((p) => (
                  <MenuItem key={p.id} value={p.id}>
                    {p.name} ({p.location})
                  </MenuItem>
                ))}
                {plants.length === 0 && !loading && (
                  <MenuItem value="">
                    <em>No plants registered</em>
                  </MenuItem>
                )}
              </Select>
            </FormControl>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            {/* Theme Toggle */}
            <Tooltip title="Toggle light/dark mode">
              <IconButton onClick={toggleTheme} color="inherit">
                {mode === 'dark' ? <Brightness7Icon /> : <Brightness4Icon />}
              </IconButton>
            </Tooltip>

            {/* Notification Bell */}
            <Tooltip title="Notifications">
              <IconButton color="inherit">
                <Badge badgeContent={3} color="error">
                  <NotificationsIcon />
                </Badge>
              </IconButton>
            </Tooltip>
          </Box>
        </Toolbar>
      </AppBar>

      {/* ─── Sidebar Drawer ─────────────────────────────────────────────────── */}
      <Drawer
        variant="permanent"
        open={!collapsed}
        sx={{
          width: activeSidebarWidth,
          flexShrink: 0,
          whiteSpace: 'nowrap',
          boxSizing: 'border-box',
          '& .MuiDrawer-paper': {
            width: activeSidebarWidth,
            boxSizing: 'border-box',
            borderRight: '1px solid',
            borderColor: 'divider',
            background: mode === 'dark' ? 'linear-gradient(180deg, #121824 0%, #0F1219 100%)' : '#FFFFFF',
            transition: (theme) => theme.transitions.create('width', {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            }),
            overflowX: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          },
        }}
      >
        <Box>
          {/* Logo Brand Header */}
          <Box
            sx={{
              height: 64,
              display: 'flex',
              alignItems: 'center',
              px: collapsed ? 2.5 : 3,
              gap: 1.5,
            }}
          >
            <Box
              sx={{
                width: 32,
                height: 32,
                borderRadius: '8px',
                background: ACCENT_GRADIENT,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 4px 12px rgba(0, 191, 166, 0.3)',
              }}
            >
              <Typography variant="h6" sx={{ color: '#fff', fontWeight: 900, fontSize: '1.1rem' }}>
                S
              </Typography>
            </Box>
            {!collapsed && (
              <Typography
                variant="h6"
                sx={{
                  fontWeight: 800,
                  background: ACCENT_GRADIENT,
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  letterSpacing: '-0.03em',
                }}
              >
                SoliZer
              </Typography>
            )}
          </Box>

          <Divider sx={{ opacity: 0.5 }} />

          {/* Navigation Links */}
          <List sx={{ px: 1.5, py: 1.5 }}>
            {menuItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <ListItem key={item.name} disablePadding sx={{ display: 'block', mb: 0.5 }}>
                  <Tooltip title={collapsed ? item.name : ''} placement="right">
                    <ListItemButton
                      onClick={() => navigate(item.path)}
                      sx={{
                        minHeight: 48,
                        justifyContent: collapsed ? 'center' : 'initial',
                        px: 2.5,
                        borderRadius: '10px',
                        bgcolor: isActive ? 'primary.main' : 'transparent',
                        color: isActive ? '#fff' : 'text.secondary',
                        '&:hover': {
                          bgcolor: isActive ? 'primary.main' : 'action.hover',
                          color: isActive ? '#fff' : 'text.primary',
                          '& .MuiListItemIcon-root': {
                            color: isActive ? '#fff' : 'primary.main',
                          },
                        },
                        transition: 'all 0.2s ease',
                      }}
                    >
                      <ListItemIcon
                        sx={{
                          minWidth: 0,
                          mr: collapsed ? 'auto' : 2,
                          justifyContent: 'center',
                          color: isActive ? '#fff' : 'text.secondary',
                        }}
                      >
                        {item.icon}
                      </ListItemIcon>
                      {!collapsed && (
                        <ListItemText
                          primary={
                            <Typography sx={{ fontWeight: isActive ? 600 : 500, fontSize: '0.875rem' }}>
                              {item.name}
                            </Typography>
                          }
                        />
                      )}
                    </ListItemButton>
                  </Tooltip>
                </ListItem>
              );
            })}
          </List>
        </Box>

        {/* Sidebar Footer / Collapse Toggle */}
        <Box>
          <Divider sx={{ opacity: 0.5 }} />
          
          {/* Collapse Button */}
          <Box sx={{ p: 1.5, display: 'flex', justifyContent: collapsed ? 'center' : 'flex-end' }}>
            <IconButton onClick={() => setCollapsed(!collapsed)} size="small" sx={{ border: '1px solid', borderColor: 'divider' }}>
              {collapsed ? <ChevronRightIcon /> : <ChevronLeftIcon />}
            </IconButton>
          </Box>
          
          {/* Version details */}
          {!collapsed && (
            <Box sx={{ px: 3, pb: 2, pt: 0.5, textAlign: 'center' }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
                SoliZer Intelligence Platform
                <br />
                v1.0.0 MVP
              </Typography>
            </Box>
          )}
        </Box>
      </Drawer>

      {/* ─── Main Content Wrapper ────────────────────────────────────────────── */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: `calc(100% - ${activeSidebarWidth}px)`,
          minHeight: '100vh',
          pt: '88px', // offset AppBar height + gap
          transition: (theme) => theme.transitions.create(['width', 'margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.enteringScreen,
          }),
        }}
      >
        {children}
      </Box>
    </Box>
  );
};
