import React, { useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import Grid from '@mui/material/Grid';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ChartTooltip,
  Legend,
} from 'recharts';
import { usePlant } from '../context/PlantContext';
import { getIrradiation } from '../services/api';
import type { IrradiationData } from '../types';
import { DateFilterBar } from '../components/DateFilterBar';

export const IrradiationPage: React.FC = () => {
  const { selectedPlantId, startDate, endDate } = usePlant();
  const [period, setPeriod] = useState<string>('daily');
  const [data, setData] = useState<IrradiationData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedPlantId) return;

    const fetchIrradiationData = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await getIrradiation(selectedPlantId, period, startDate, endDate);
        setData(result);
      } catch (err) {
        console.error('Error fetching irradiation:', err);
        setError('Failed to load solar resource data.');
      } finally {
        setLoading(false);
      }
    };

    fetchIrradiationData();
  }, [selectedPlantId, period, startDate, endDate]);

  const handlePeriodChange = (
    _event: React.MouseEvent<HTMLElement>,
    newPeriod: string | null,
  ) => {
    if (newPeriod !== null) {
      setPeriod(newPeriod);
    }
  };

  if (!selectedPlantId) {
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h5" color="text.secondary">
          Please select or create a plant profile first.
        </Typography>
      </Box>
    );
  }

  const chartData = data?.data || [];

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
        <Typography variant="h4" sx={{ fontWeight: 'bold', color: 'primary.main' }}>
          Irradiation Analysis
        </Typography>
        <ToggleButtonGroup
          color="primary"
          value={period}
          exclusive
          onChange={handlePeriodChange}
          size="small"
          sx={{ bgcolor: 'rgba(255, 255, 255, 0.05)' }}
        >
          <ToggleButton value="daily">Daily</ToggleButton>
          <ToggleButton value="monthly">Monthly</ToggleButton>
          <ToggleButton value="yearly">Yearly</ToggleButton>
        </ToggleButtonGroup>
      </Box>

      <DateFilterBar />

      {loading && !data ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 5 }}>
          <CircularProgress color="primary" />
        </Box>
      ) : error ? (
        <Typography color="error">{error}</Typography>
      ) : data ? (
        <>
          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 4 }}>
              <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">Total Period Irradiation</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 'bold', my: 1, color: 'warning.main' }}>
                    {(data.total_ghi_kwh_m2).toLocaleString(undefined, { maximumFractionDigits: 1 })} kWh/m²
                  </Typography>
                  <Typography variant="caption" color="text.secondary">Total solar energy received per square meter</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">Average Daily Irradiation</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 'bold', my: 1, color: 'warning.main' }}>
                    {(data.average_daily_ghi / 100.0).toLocaleString(undefined, { maximumFractionDigits: 2 })} kWh/m²/day
                  </Typography>
                  <Typography variant="caption" color="text.secondary">Daily energy density (GHI / POA average)</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">Peak Sun Hours (PSH)</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 'bold', my: 1, color: 'warning.main' }}>
                    {(data.peak_sun_hours).toLocaleString(undefined, { maximumFractionDigits: 1 })} Hours
                  </Typography>
                  <Typography variant="caption" color="text.secondary">Equivalent hours at 1,000 W/m² intensity</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', p: 2 }}>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>Solar Irradiation Trend ({period.toUpperCase()})</Typography>
                  <Box sx={{ height: 280, width: '100%' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <defs>
                          <linearGradient id="colorIrr" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#ffa000" stopOpacity={0.4}/>
                            <stop offset="95%" stopColor="#ffa000" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
                        <XAxis dataKey="date" stroke="rgba(255, 255, 255, 0.5)" tick={{ fontSize: 10 }} />
                        <YAxis stroke="rgba(255, 255, 255, 0.5)" tick={{ fontSize: 10 }} label={{ value: 'Irradiation (kWh/m²)', angle: -90, position: 'insideLeft', style: { fill: 'rgba(255,255,255,0.5)', fontSize: 10 } }} />
                        <ChartTooltip contentStyle={{ background: 'rgba(20, 20, 20, 0.9)', border: '1px solid rgba(255, 255, 255, 0.1)' }} />
                        <Legend />
                        <Area type="monotone" dataKey="ghi_kwh_m2" name="GHI/POA (kWh/m²)" stroke="#ffa000" strokeWidth={2} fillOpacity={1} fill="url(#colorIrr)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', p: 2 }}>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>Peak Sun Hours (PSH) Trend ({period.toUpperCase()})</Typography>
                  <Box sx={{ height: 280, width: '100%' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
                        <XAxis dataKey="date" stroke="rgba(255, 255, 255, 0.5)" tick={{ fontSize: 10 }} />
                        <YAxis stroke="rgba(255, 255, 255, 0.5)" tick={{ fontSize: 10 }} label={{ value: 'Peak Sun Hours', angle: -90, position: 'insideLeft', style: { fill: 'rgba(255,255,255,0.5)', fontSize: 10 } }} />
                        <ChartTooltip contentStyle={{ background: 'rgba(20, 20, 20, 0.9)', border: '1px solid rgba(255, 255, 255, 0.1)' }} />
                        <Legend />
                        <Line type="monotone" dataKey="peak_sun_hours" name="Equivalent Peak Hours" stroke="#00bfa6" strokeWidth={2} dot={period !== 'daily'} />
                      </LineChart>
                    </ResponsiveContainer>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', p: 3 }}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 1.5 }}>Irradiation Metering Overview</Typography>
              <Typography variant="body1">
                The plant's pyranometer registers active solar resource data. Total registered irradiation is <b>{(data.total_ghi_kwh_m2).toLocaleString(undefined, { maximumFractionDigits: 1 })} kWh/m²</b>.
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
                Irradiation is the direct catalyst for solar cell generation. Deviations in performance relative to this resource directly influence the Performance Ratio (PR) engine.
              </Typography>
            </CardContent>
          </Card>
        </>
      ) : (
        <Typography color="text.secondary">No solar irradiation resource records loaded.</Typography>
      )}
    </Box>
  );
};
