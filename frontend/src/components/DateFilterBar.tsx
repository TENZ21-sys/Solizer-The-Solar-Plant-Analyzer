import React, { useEffect, useState } from 'react';
import {
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Typography,
  Paper,
  Button,
} from '@mui/material';
import CalendarMonthRoundedIcon from '@mui/icons-material/CalendarMonthRounded';
import { usePlant } from '../context/PlantContext';

export const DateFilterBar: React.FC = () => {
  const { startDate, endDate, setDateRange } = usePlant();
  const [filterType, setFilterType] = useState<string>('all');
  const [customStart, setCustomStart] = useState<string>('');
  const [customEnd, setCustomEnd] = useState<string>('');

  // Sync dropdown with global state on mount / change
  useEffect(() => {
    if (!startDate && !endDate) {
      setFilterType('all');
    } else if (startDate === '2023-05-01' && endDate === '2024-04-30') {
      setFilterType('2023-2024');
    } else if (startDate === '2024-05-01' && endDate === '2025-04-30') {
      setFilterType('2024-2025');
    } else if (startDate === '2025-05-01' && endDate === '2026-04-30') {
      setFilterType('2025-2026');
    } else {
      setFilterType('custom');
      setCustomStart(startDate || '');
      setCustomEnd(endDate || '');
    }
  }, [startDate, endDate]);

  const handleFilterTypeChange = (e: any) => {
    const type = e.target.value;
    setFilterType(type);

    if (type === 'all') {
      setDateRange(undefined, undefined);
    } else if (type === '2023-2024') {
      setDateRange('2023-05-01', '2024-04-30');
    } else if (type === '2024-2025') {
      setDateRange('2024-05-01', '2025-04-30');
    } else if (type === '2025-2026') {
      setDateRange('2025-05-01', '2026-04-30');
    } else if (type === 'custom') {
      // Keep existing custom values or default to empty
      setDateRange(customStart || undefined, customEnd || undefined);
    }
  };

  const handleCustomStartChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setCustomStart(val);
    setDateRange(val || undefined, customEnd || undefined);
  };

  const handleCustomEndChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setCustomEnd(val);
    setDateRange(customStart || undefined, val || undefined);
  };

  const handleReset = () => {
    setDateRange(undefined, undefined);
  };

  return (
    <Paper
      elevation={0}
      sx={{
        p: 2,
        mb: 3,
        borderRadius: 3,
        border: '1px solid',
        borderColor: 'divider',
        background: (theme) =>
          theme.palette.mode === 'dark'
            ? 'rgba(30, 41, 59, 0.45)'
            : 'rgba(255, 255, 255, 0.8)',
        backdropFilter: 'blur(16px)',
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 2,
        transition: 'all 0.3s ease',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <CalendarMonthRoundedIcon sx={{ color: 'primary.main' }} />
        <Box>
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            Analysis Period
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Filter all metrics and charts dynamically
          </Typography>
        </Box>
      </Box>

      <Box
        sx={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: 2,
          flexGrow: { xs: 1, md: 0 },
        }}
      >
        <FormControl size="small" sx={{ minWidth: 200, flexGrow: 1 }}>
          <InputLabel id="period-select-label">Select Period</InputLabel>
          <Select
            labelId="period-select-label"
            id="period-select"
            value={filterType}
            label="Select Period"
            onChange={handleFilterTypeChange}
            sx={{ borderRadius: 2 }}
          >
            <MenuItem value="all">All Time (Unfiltered)</MenuItem>
            <MenuItem value="2023-2024">Study Year: 2023-2024 (May 1 - Apr 30)</MenuItem>
            <MenuItem value="2024-2025">Study Year: 2024-2025 (May 1 - Apr 30)</MenuItem>
            <MenuItem value="2025-2026">Study Year: 2025-2026 (May 1 - Apr 30)</MenuItem>
            <MenuItem value="custom">Custom Date Range...</MenuItem>
          </Select>
        </FormControl>

        {filterType === 'custom' && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexGrow: 1 }}>
            <TextField
              size="small"
              label="Start Date"
              type="date"
              value={customStart}
              onChange={handleCustomStartChange}
              slotProps={{ inputLabel: { shrink: true } }}
              sx={{ minWidth: 140, '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
            />
            <Typography variant="body2" color="text.secondary">
              to
            </Typography>
            <TextField
              size="small"
              label="End Date"
              type="date"
              value={customEnd}
              onChange={handleCustomEndChange}
              slotProps={{ inputLabel: { shrink: true } }}
              sx={{ minWidth: 140, '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
            />
          </Box>
        )}

        {(startDate || endDate) && (
          <Button
            size="small"
            variant="text"
            onClick={handleReset}
            sx={{ borderRadius: 2, textTransform: 'none', fontWeight: 600 }}
          >
            Reset Filters
          </Button>
        )}
      </Box>
    </Paper>
  );
};
