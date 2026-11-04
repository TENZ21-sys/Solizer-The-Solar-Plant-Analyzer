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
  PieChart,
  Pie,
  Cell,
  Legend,
  Tooltip as ChartTooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts';
import { usePlant } from '../context/PlantContext';
import { getLosses } from '../services/api';
import type { LossBreakdown } from '../types';
import { DateFilterBar } from '../components/DateFilterBar';

export const LossesPage: React.FC = () => {
  const { selectedPlantId, startDate, endDate } = usePlant();
  const [period, setPeriod] = useState<string>('monthly');
  const [data, setData] = useState<LossBreakdown | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedPlantId) return;

    const fetchLossData = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await getLosses(selectedPlantId, period, startDate, endDate);
        setData(result);
      } catch (err) {
        console.error('Error fetching losses:', err);
        setError('Failed to load energy loss analysis.');
      } finally {
        setLoading(false);
      }
    };

    fetchLossData();
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

  const chartData = data?.time_series.map((pt) => ({
    date: pt.date,
    'Grid Failure': period === 'daily' ? pt.grid_failure_kwh : pt.grid_failure_kwh / 1000,
    'Curtailment': period === 'daily' ? pt.curtailment_kwh : pt.curtailment_kwh / 1000,
    'Machine Loss': period === 'daily' ? pt.machine_loss_kwh : pt.machine_loss_kwh / 1000,
  })) || [];

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
        <Typography variant="h4" sx={{ fontWeight: 'bold', color: 'primary.main' }}>
          Loss Analysis
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
            <Grid size={{ xs: 12, md: 6 }}>
              <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">Total Energy Losses</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 'bold', my: 1, color: 'error.main' }}>
                    {(data.total_loss_kwh / 1000.0).toLocaleString(undefined, { maximumFractionDigits: 1 })} MWh
                  </Typography>
                  <Typography variant="caption" color="text.secondary">Sum of grid outages, curtailment, and faults</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">Loss Ratio (%)</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 'bold', my: 1, color: 'error.main' }}>
                    {data.total_loss_percentage.toFixed(2)}%
                  </Typography>
                  <Typography variant="caption" color="text.secondary">Percentage of total possible generation</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 4 }}>
              <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', p: 2, height: '100%' }}>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>Loss Category Breakdown</Typography>
                  <Box sx={{ height: 250, width: '100%' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={data.categories.map((c) => ({ name: c.category, value: c.loss_kwh }))}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={80}
                          paddingAngle={5}
                          dataKey="value"
                        >
                          {data.categories.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <ChartTooltip contentStyle={{ background: 'rgba(20, 20, 20, 0.9)', border: '1px solid rgba(255, 255, 255, 0.1)' }} />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 8 }}>
              <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', p: 2 }}>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>Losses Trend Over Time ({period.toUpperCase()})</Typography>
                  <Box sx={{ height: 250, width: '100%' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
                        <XAxis dataKey="date" stroke="rgba(255, 255, 255, 0.5)" tick={{ fontSize: 10 }} />
                        <YAxis stroke="rgba(255, 255, 255, 0.5)" tick={{ fontSize: 10 }} label={{ value: period === 'daily' ? 'Losses (kWh)' : 'Losses (MWh)', angle: -90, position: 'insideLeft', style: { fill: 'rgba(255,255,255,0.5)', fontSize: 10 } }} />
                        <ChartTooltip contentStyle={{ background: 'rgba(20, 20, 20, 0.9)', border: '1px solid rgba(255, 255, 255, 0.1)' }} />
                        <Legend />
                        <Bar dataKey="Grid Failure" stackId="a" fill="#ef5350" />
                        <Bar dataKey="Curtailment" stackId="a" fill="#ff9800" />
                        <Bar dataKey="Machine Loss" stackId="a" fill="#ffa726" />
                      </BarChart>
                    </ResponsiveContainer>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 6 }}>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>Detailed Losses Breakdown</Typography>
              <TableContainer component={Paper} sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell><Typography variant="subtitle2">Loss Category</Typography></TableCell>
                      <TableCell><Typography variant="subtitle2">Energy Lost (MWh)</Typography></TableCell>
                      <TableCell><Typography variant="subtitle2">% of Possible Gen</Typography></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {data.categories.map((cat, i) => (
                      <TableRow key={i}>
                        <TableCell sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                          <Box sx={{ width: 12, height: 12, borderRadius: '50%', bgcolor: cat.color }} />
                          {cat.category}
                        </TableCell>
                        <TableCell>{(cat.loss_kwh / 1000.0).toFixed(2)} MWh</TableCell>
                        <TableCell>{cat.loss_percentage.toFixed(2)}%</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', p: 2, height: '100%' }}>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>Impact Summary</Typography>
                  <Typography variant="body1" sx={{ mb: 2 }}>
                    Operational losses represent a total of <b>{(data.total_loss_kwh / 1000.0).toFixed(2)} MWh</b> of un-exported power. 
                    Monitoring and mitigating these outages is primary to ensuring contractual yield margins.
                  </Typography>
                  <Box sx={{ p: 2, bgcolor: 'rgba(0, 0, 0, 0.2)', borderRadius: 2 }}>
                    <Typography variant="subtitle2" color="warning.main" sx={{ fontWeight: 600, mb: 0.5 }}>Did you know?</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Grid-related events (outages and curtailments) are typically external factors. Machine losses, however, can be reduced via predictive maintenance and string audits.
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </>
      ) : (
        <Typography color="text.secondary">No operational loss data found. Verify imported data is present.</Typography>
      )}
    </Box>
  );
};
