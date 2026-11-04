import React, { useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  ToggleButtonGroup,
  ToggleButton,
  TableContainer,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Paper,
} from '@mui/material';
import Grid from '@mui/material/Grid';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ChartTooltip,
  Legend,
} from 'recharts';
import { usePlant } from '../context/PlantContext';
import { getGeneration } from '../services/api';
import type { GenerationData } from '../types';
import { DateFilterBar } from '../components/DateFilterBar';

export const PerformancePage: React.FC = () => {
  const { selectedPlantId, startDate, endDate } = usePlant();
  const [period, setPeriod] = useState<string>('daily');
  const [data, setData] = useState<GenerationData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedPlantId) return;

    const fetchGenerationData = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await getGeneration(selectedPlantId, period, startDate, endDate);
        setData(result);
      } catch (err) {
        console.error('Error fetching generation:', err);
        setError('Failed to load performance metrics.');
      } finally {
        setLoading(false);
      }
    };

    fetchGenerationData();
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
          Plant Performance Analysis
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
                  <Typography variant="subtitle2" color="text.secondary">Total Actual Generation</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 'bold', my: 1, color: 'success.main' }}>
                    {(data.total_actual_kwh / 1000.0).toLocaleString(undefined, { maximumFractionDigits: 1 })} MWh
                  </Typography>
                  <Typography variant="caption" color="text.secondary">Sum across selected period</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">Total Expected Generation</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 'bold', my: 1, color: 'info.main' }}>
                    {(data.total_expected_kwh / 1000.0).toLocaleString(undefined, { maximumFractionDigits: 1 })} MWh
                  </Typography>
                  <Typography variant="caption" color="text.secondary">Based on available solar resource</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">Average Performance Ratio</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 'bold', my: 1, color: 'warning.main' }}>
                    {data.average_pr.toFixed(2)}%
                  </Typography>
                  <Typography variant="caption" color="text.secondary">System conversion efficiency</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', p: 2 }}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                Generation Timeline Comparison (MWh)
              </Typography>
              <Box sx={{ height: 350, width: '100%' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={data.data.map((d) => ({
                      ...d,
                      actual_mwh: parseFloat((d.actual_kwh / 1000.0).toFixed(2)),
                      expected_mwh: parseFloat((d.expected_kwh / 1000.0).toFixed(2)),
                    }))}
                    margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#00e676" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#00e676" stopOpacity={0.0} />
                      </linearGradient>
                      <linearGradient id="colorExpected" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#29b6f6" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#29b6f6" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
                    <XAxis dataKey="date" stroke="rgba(255, 255, 255, 0.5)" tick={{ fontSize: 10 }} />
                    <YAxis stroke="rgba(255, 255, 255, 0.5)" tick={{ fontSize: 10 }} />
                    <ChartTooltip
                      contentStyle={{
                        background: 'rgba(20, 20, 20, 0.9)',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: 8,
                      }}
                    />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="actual_mwh"
                      name="Actual Gen (MWh)"
                      stroke="#00e676"
                      fillOpacity={1}
                      fill="url(#colorActual)"
                    />
                    <Area
                      type="monotone"
                      dataKey="expected_mwh"
                      name="Expected Gen (MWh)"
                      stroke="#29b6f6"
                      fillOpacity={1}
                      fill="url(#colorExpected)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>

          <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', p: 2 }}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                Performance Ratio (%) Trend
              </Typography>
              <Box sx={{ height: 350, width: '100%' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={data.data.map((d) => ({
                      ...d,
                      pr: d.pr !== undefined ? parseFloat(d.pr.toFixed(2)) : 0.0,
                    }))}
                    margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient id="colorPR" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#ffb74d" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#ffb74d" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
                    <XAxis dataKey="date" stroke="rgba(255, 255, 255, 0.5)" tick={{ fontSize: 10 }} />
                    <YAxis domain={[50, 100]} stroke="rgba(255, 255, 255, 0.5)" tick={{ fontSize: 10 }} />
                    <ChartTooltip
                      contentStyle={{
                        background: 'rgba(20, 20, 20, 0.9)',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: 8,
                      }}
                    />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="pr"
                      name="Performance Ratio (%)"
                      stroke="#ffb74d"
                      fillOpacity={1}
                      fill="url(#colorPR)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>

          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Raw Generation & Yield Records
          </Typography>
          <TableContainer component={Paper} sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', maxHeight: 400 }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ background: 'rgba(30, 30, 30, 0.95)' }}><Typography variant="subtitle2">Date/Period</Typography></TableCell>
                  <TableCell sx={{ background: 'rgba(30, 30, 30, 0.95)' }}><Typography variant="subtitle2">Actual Generation</Typography></TableCell>
                  <TableCell sx={{ background: 'rgba(30, 30, 30, 0.95)' }}><Typography variant="subtitle2">Expected Generation</Typography></TableCell>
                  <TableCell sx={{ background: 'rgba(30, 30, 30, 0.95)' }}><Typography variant="subtitle2">Deviation</Typography></TableCell>
                  <TableCell sx={{ background: 'rgba(30, 30, 30, 0.95)' }}><Typography variant="subtitle2">Irradiation</Typography></TableCell>
                  <TableCell sx={{ background: 'rgba(30, 30, 30, 0.95)' }}><Typography variant="subtitle2">Specific Yield</Typography></TableCell>
                  <TableCell sx={{ background: 'rgba(30, 30, 30, 0.95)' }}><Typography variant="subtitle2">PR (%)</Typography></TableCell>
                  <TableCell sx={{ background: 'rgba(30, 30, 30, 0.95)' }}><Typography variant="subtitle2">CUF (%)</Typography></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.data.map((row, i) => {
                  const dev = row.actual_kwh - row.expected_kwh;
                  const isDaily = period === 'daily';
                  const unit = isDaily ? 'kWh' : 'MWh';
                  const divisor = isDaily ? 1.0 : 1000.0;
                  const irrVal = row.irradiation ? row.irradiation / 1000.0 : 0.0;
                  
                  return (
                    <TableRow key={i}>
                      <TableCell>{row.date}</TableCell>
                      <TableCell>{(row.actual_kwh / divisor).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 2 })} {unit}</TableCell>
                      <TableCell>{(row.expected_kwh / divisor).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 2 })} {unit}</TableCell>
                      <TableCell sx={{ color: dev >= 0 ? 'success.main' : 'error.main' }}>
                        {dev >= 0 ? '+' : ''}{(dev / divisor).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 2 })} {unit}
                      </TableCell>
                      <TableCell>{irrVal.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} kWh/m²</TableCell>
                      <TableCell>{row.specific_yield !== undefined ? `${row.specific_yield.toFixed(1)} kWh/kWp` : '-'}</TableCell>
                      <TableCell>{row.pr !== undefined ? `${row.pr.toFixed(2)}%` : '-'}</TableCell>
                      <TableCell>{row.cuf !== undefined ? `${row.cuf.toFixed(2)}%` : '-'}</TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      ) : null}
    </Box>
  );
};
