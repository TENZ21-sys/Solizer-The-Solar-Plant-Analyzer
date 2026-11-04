import React, { useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  TableContainer,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Paper,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import Grid from '@mui/material/Grid';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ChartTooltip,
  Legend,
} from 'recharts';
import { usePlant } from '../context/PlantContext';
import { getDegradation } from '../services/api';
import type { DegradationData } from '../types';
import { DateFilterBar } from '../components/DateFilterBar';

export const DegradationPage: React.FC = () => {
  const { selectedPlantId, startDate, endDate } = usePlant();
  const [period, setPeriod] = useState<string>('yearly');
  const [data, setData] = useState<DegradationData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedPlantId) return;

    const fetchDegradationData = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await getDegradation(selectedPlantId, period, startDate, endDate);
        setData(result);
      } catch (err) {
        console.error('Error fetching degradation:', err);
        setError('Failed to load YoY degradation diagnostics.');
      } finally {
        setLoading(false);
      }
    };

    fetchDegradationData();
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

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
        <Typography variant="h4" sx={{ fontWeight: 'bold', color: 'primary.main' }}>
          Degradation Analysis
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
            <Grid size={{ xs: 12, md: 3 }}>
              <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">Observed Degradation Rate</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 'bold', my: 1, color: 'error.main' }}>
                    {data.annual_degradation_rate.toFixed(2)}% / yr
                  </Typography>
                  <Typography variant="caption" color="text.secondary">Annual Performance Ratio decline</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">Cumulative Degradation</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 'bold', my: 1, color: 'error.main' }}>
                    {data.cumulative_degradation.toFixed(2)}%
                  </Typography>
                  <Typography variant="caption" color="text.secondary">Total capacity loss over study period</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">Expected Degradation</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 'bold', my: 1, color: 'info.main' }}>
                    {data.expected_degradation !== undefined ? `${data.expected_degradation.toFixed(2)}%` : '-'}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">Target degradation based on age</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">Expected Remaining Lifetime</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 'bold', my: 1, color: 'success.main' }}>
                    {data.expected_lifetime_years.toFixed(1)} Years
                  </Typography>
                  <Typography variant="caption" color="text.secondary">Until PR drops below 50% threshold</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', p: 2 }}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                Performance Ratio Decline Trendline ({period.toUpperCase()})
              </Typography>
              <Box sx={{ height: 300, width: '100%' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.trend} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
                    <XAxis dataKey="year" stroke="rgba(255, 255, 255, 0.5)" />
                    <YAxis domain={[0, 100]} stroke="rgba(255, 255, 255, 0.5)" />
                    <ChartTooltip contentStyle={{ background: 'rgba(20, 20, 20, 0.9)', border: '1px solid rgba(255, 255, 255, 0.1)' }} />
                    <Legend />
                    <Line type="monotone" dataKey="pr" name="Actual YoY PR (%)" stroke="#1e88e5" strokeWidth={period === 'daily' ? 1.5 : 3} dot={period !== 'daily'} activeDot={{ r: 8 }} />
                    <Line type="monotone" dataKey="expected_pr" name="Expected PR Target (%)" stroke="#e53935" strokeDasharray="5 5" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>

          <Typography variant="h6" sx={{ fontWeight: 600 }}>Yearly Performance Breakdown</Typography>
          <TableContainer component={Paper} sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell><Typography variant="subtitle2">Year</Typography></TableCell>
                  <TableCell><Typography variant="subtitle2">Observed PR (%)</Typography></TableCell>
                  <TableCell><Typography variant="subtitle2">Target PR (%)</Typography></TableCell>
                  <TableCell><Typography variant="subtitle2">Shortfall (%)</Typography></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.trend.map((row, i) => {
                  const diff = row.expected_pr - row.pr;
                  return (
                    <TableRow key={i}>
                      <TableCell>{row.year}</TableCell>
                      <TableCell>{row.pr.toFixed(2)}%</TableCell>
                      <TableCell>{row.expected_pr.toFixed(2)}%</TableCell>
                      <TableCell sx={{ color: diff <= 0 ? 'success.main' : 'error.main' }}>
                        {diff <= 0 ? '+' : ''}{(-diff).toFixed(2)}%
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      ) : (
        <Typography color="text.secondary">No degradation data found. Ensure historical records span multiple months.</Typography>
      )}
    </Box>
  );
};
