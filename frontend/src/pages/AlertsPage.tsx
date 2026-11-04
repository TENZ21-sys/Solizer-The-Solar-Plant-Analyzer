import React, { useEffect, useState } from 'react';
import {
  Box,
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
} from '@mui/material';
import { usePlant } from '../context/PlantContext';
import { getAlerts } from '../services/api';
import type { Alert } from '../types';

export const AlertsPage: React.FC = () => {
  const { selectedPlantId } = usePlant();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedPlantId) return;

    const fetchAlertsData = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await getAlerts(selectedPlantId);
        setAlerts(result);
      } catch (err) {
        console.error('Error fetching alerts:', err);
        setError('Failed to load active system alerts.');
      } finally {
        setLoading(false);
      }
    };

    fetchAlertsData();
  }, [selectedPlantId]);

  if (!selectedPlantId) {
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h5" color="text.secondary">
          Please select or create a plant profile first.
        </Typography>
      </Box>
    );
  }

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return 'error';
      case 'warning':
        return 'warning';
      case 'info':
      default:
        return 'info';
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Typography variant="h4" sx={{ fontWeight: 'bold', color: 'primary.main' }}>
        Operational Alerts Overview
      </Typography>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 5 }}>
          <CircularProgress color="primary" />
        </Box>
      ) : error ? (
        <Typography color="error">{error}</Typography>
      ) : alerts.length > 0 ? (
        <TableContainer component={Paper} sx={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell><Typography variant="subtitle2">Alert Date</Typography></TableCell>
                <TableCell><Typography variant="subtitle2">Severity</Typography></TableCell>
                <TableCell><Typography variant="subtitle2">Category</Typography></TableCell>
                <TableCell><Typography variant="subtitle2">Alert Message</Typography></TableCell>
                <TableCell><Typography variant="subtitle2">Status</Typography></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {alerts.map((row, i) => (
                <TableRow key={i}>
                  <TableCell>{new Date(row.created_at).toLocaleDateString()}</TableCell>
                  <TableCell>
                    <Chip label={row.severity.toUpperCase()} color={getSeverityColor(row.severity)} size="small" />
                  </TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>{row.category}</TableCell>
                  <TableCell>{row.message}</TableCell>
                  <TableCell>
                    <Chip label={row.status.toUpperCase()} variant="outlined" size="small" color={row.status === 'active' ? 'error' : 'success'} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
        <Typography color="text.secondary">All operational systems are healthy. No active alerts present.</Typography>
      )}
    </Box>
  );
};
