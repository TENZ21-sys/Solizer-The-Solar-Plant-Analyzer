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
  Chip,
  TableSortLabel,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import Grid from '@mui/material/Grid';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ChartTooltip,
  Legend,
  LineChart,
  Line,
} from 'recharts';
import { usePlant } from '../context/PlantContext';
import { getInverters } from '../services/api';
import type { InverterSummary, InverterTimeSeriesPoint } from '../types';
import { DateFilterBar } from '../components/DateFilterBar';

export const InvertersPage: React.FC = () => {
  const { selectedPlantId, startDate, endDate } = usePlant();
  const [period, setPeriod] = useState<string>('monthly');
  const [inverters, setInverters] = useState<InverterSummary[]>([]);
  const [timeSeries, setTimeSeries] = useState<InverterTimeSeriesPoint[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [orderBy, setOrderBy] = useState<keyof InverterSummary>('performance_ratio');
  const [order, setOrder] = useState<'asc' | 'desc'>('desc');

  const handleRequestSort = (property: keyof InverterSummary) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  const sortedInverters = [...inverters].sort((a, b) => {
    const valA = a[orderBy];
    const valB = b[orderBy];

    if (valA === undefined) return 1;
    if (valB === undefined) return -1;

    if (typeof valA === 'string') {
      return order === 'asc'
        ? valA.localeCompare(valB as string)
        : (valB as string).localeCompare(valA);
    } else {
      return order === 'asc'
        ? (valA as number) - (valB as number)
        : (valB as number) - (valA as number);
    }
  });

  useEffect(() => {
    if (!selectedPlantId) return;

    const fetchInverterData = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await getInverters(selectedPlantId, period, startDate, endDate);
        setInverters(result.summaries);
        setTimeSeries(result.time_series);
      } catch (err) {
        console.error('Error fetching inverters:', err);
        setError('Failed to load inverter comparative statistics.');
      } finally {
        setLoading(false);
      }
    };

    fetchInverterData();
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

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy':
        return 'success';
      case 'warning':
        return 'warning';
      case 'critical':
        return 'error';
      default:
        return 'default';
    }
  };

  // Pivot the flat timeSeries array into a Recharts-friendly format
  const pivotedDataMap: Record<string, Record<string, number>> = {};
  const inverterNamesSet = new Set<string>();

  timeSeries.forEach((pt) => {
    inverterNamesSet.add(pt.inverter_name);
    if (!pivotedDataMap[pt.date]) {
      pivotedDataMap[pt.date] = {};
    }
    pivotedDataMap[pt.date][pt.inverter_name] = pt.pr;
  });

  const pivotedChartData = Object.keys(pivotedDataMap).sort().map((date) => ({
    date,
    ...pivotedDataMap[date],
  }));

  const inverterNames = Array.from(inverterNamesSet);
  const colors = ['#00e676', '#00bfa6', '#1e88e5', '#ff9800', '#ef5350', '#b388ff', '#f50057'];

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
        <Typography variant="h4" sx={{ fontWeight: 'bold', color: 'primary.main' }}>
          Inverter Analysis
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

      {loading && inverters.length === 0 ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 5 }}>
          <CircularProgress color="primary" />
        </Box>
      ) : error ? (
        <Typography color="error">{error}</Typography>
      ) : inverters.length > 0 ? (
        <>
          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 4 }}>
              <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">Total Inverters</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 'bold', my: 1 }}>
                    {inverters.length} Units
                  </Typography>
                  <Typography variant="caption" color="text.secondary">Configured plant topology</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">Average Inverter PR</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 'bold', my: 1, color: 'warning.main' }}>
                    {(inverters.reduce((sum, inv) => sum + inv.performance_ratio, 0) / inverters.length).toFixed(2)}%
                  </Typography>
                  <Typography variant="caption" color="text.secondary">Individual average conversion efficiency</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
                <CardContent>
                  <Typography variant="subtitle2" color="text.secondary">Anomalous / Warning Units</Typography>
                  <Typography variant="h4" sx={{ fontWeight: 'bold', my: 1, color: 'error.main' }}>
                    {inverters.filter(inv => inv.status !== 'healthy').length} Units
                  </Typography>
                  <Typography variant="caption" color="text.secondary">Requiring technical inspection</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {timeSeries.length > 0 && (
            <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', p: 2 }}>
              <CardContent>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>Inverter PR Comparison Over Time ({period.toUpperCase()})</Typography>
                <Box sx={{ height: 300, width: '100%' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={pivotedChartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
                      <XAxis dataKey="date" stroke="rgba(255, 255, 255, 0.5)" tick={{ fontSize: 10 }} />
                      <YAxis stroke="rgba(255, 255, 255, 0.5)" tick={{ fontSize: 10 }} domain={[0, 100]} />
                      <ChartTooltip contentStyle={{ background: 'rgba(20, 20, 20, 0.9)', border: '1px solid rgba(255, 255, 255, 0.1)' }} />
                      <Legend />
                      {inverterNames.map((name, idx) => (
                        <Line
                          key={name}
                          type="monotone"
                          dataKey={name}
                          stroke={colors[idx % colors.length]}
                          strokeWidth={period === 'daily' ? 1.2 : 2.5}
                          dot={period !== 'daily'}
                        />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              </CardContent>
            </Card>
          )}

          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', p: 2 }}>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>Total Inverter Generation (MWh)</Typography>
                  <Box sx={{ height: 250, width: '100%' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={inverters.map(inv => ({ name: inv.name, gen: parseFloat((inv.total_generation_kwh / 1000.0).toFixed(2)) }))}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
                        <XAxis dataKey="name" stroke="rgba(255, 255, 255, 0.5)" tick={{ fontSize: 10 }} />
                        <YAxis stroke="rgba(255, 255, 255, 0.5)" tick={{ fontSize: 10 }} />
                        <ChartTooltip contentStyle={{ background: 'rgba(20, 20, 20, 0.9)', border: '1px solid rgba(255, 255, 255, 0.1)' }} />
                        <Bar dataKey="gen" fill="#00e676" />
                      </BarChart>
                    </ResponsiveContainer>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', p: 2 }}>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>Average Performance Ratio (%)</Typography>
                  <Box sx={{ height: 250, width: '100%' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={inverters.map(inv => ({ name: inv.name, pr: parseFloat(inv.performance_ratio.toFixed(2)) }))}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
                        <XAxis dataKey="name" stroke="rgba(255, 255, 255, 0.5)" tick={{ fontSize: 10 }} />
                        <YAxis stroke="rgba(255, 255, 255, 0.5)" tick={{ fontSize: 10 }} />
                        <ChartTooltip contentStyle={{ background: 'rgba(20, 20, 20, 0.9)', border: '1px solid rgba(255, 255, 255, 0.1)' }} />
                        <Bar dataKey="pr" fill="#00bfa6" />
                      </BarChart>
                    </ResponsiveContainer>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Typography variant="h6" sx={{ fontWeight: 600 }}>Inverter Rankings & Details</Typography>
          <TableContainer component={Paper} sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>
                    <TableSortLabel
                      active={orderBy === 'name'}
                      direction={orderBy === 'name' ? order : 'desc'}
                      onClick={() => handleRequestSort('name')}
                    >
                      Inverter Name
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>
                    <TableSortLabel
                      active={orderBy === 'total_generation_kwh'}
                      direction={orderBy === 'total_generation_kwh' ? order : 'desc'}
                      onClick={() => handleRequestSort('total_generation_kwh')}
                    >
                      Generation (MWh)
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>
                    <TableSortLabel
                      active={orderBy === 'specific_yield'}
                      direction={orderBy === 'specific_yield' ? order : 'desc'}
                      onClick={() => handleRequestSort('specific_yield')}
                    >
                      Specific Yield (kWh/kWp)
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>
                    <TableSortLabel
                      active={orderBy === 'machine_loss_kwh'}
                      direction={orderBy === 'machine_loss_kwh' ? order : 'desc'}
                      onClick={() => handleRequestSort('machine_loss_kwh')}
                    >
                      Machine Loss (kWh)
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>
                    <TableSortLabel
                      active={orderBy === 'performance_ratio'}
                      direction={orderBy === 'performance_ratio' ? order : 'desc'}
                      onClick={() => handleRequestSort('performance_ratio')}
                    >
                      PR (%)
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>
                    <TableSortLabel
                      active={orderBy === 'availability'}
                      direction={orderBy === 'availability' ? order : 'desc'}
                      onClick={() => handleRequestSort('availability')}
                    >
                      Availability (%)
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>
                    <TableSortLabel
                      active={orderBy === 'status'}
                      direction={orderBy === 'status' ? order : 'desc'}
                      onClick={() => handleRequestSort('status')}
                    >
                      Status
                    </TableSortLabel>
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {sortedInverters.map((inv, i) => (
                  <TableRow key={i}>
                    <TableCell sx={{ fontWeight: 600 }}>{inv.name}</TableCell>
                    <TableCell>{(inv.total_generation_kwh / 1000.0).toFixed(2)}</TableCell>
                    <TableCell>{inv.specific_yield !== undefined ? inv.specific_yield.toFixed(1) : '-'}</TableCell>
                    <TableCell>{inv.machine_loss_kwh !== undefined ? inv.machine_loss_kwh.toLocaleString(undefined, { maximumFractionDigits: 1 }) : '-'}</TableCell>
                    <TableCell>{inv.performance_ratio.toFixed(2)}%</TableCell>
                    <TableCell>{inv.availability.toFixed(2)}%</TableCell>
                    <TableCell>
                      <Chip label={inv.status.toUpperCase()} color={getStatusColor(inv.status)} size="small" />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      ) : (
        <Typography color="text.secondary">No inverter records loaded. Import XLSX data to view detailed analytics.</Typography>
      )}
    </Box>
  );
};
