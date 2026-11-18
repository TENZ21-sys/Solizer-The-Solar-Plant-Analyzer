import React, { useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Button,
  TableContainer,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Paper,
  Alert,
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import FileDownloadRoundedIcon from '@mui/icons-material/FileDownloadRounded';
import PictureAsPdfRoundedIcon from '@mui/icons-material/PictureAsPdfRounded';
import DescriptionRoundedIcon from '@mui/icons-material/DescriptionRounded';
import CloudUploadRoundedIcon from '@mui/icons-material/CloudUploadRounded';
import BusinessRoundedIcon from '@mui/icons-material/BusinessRounded';
import DeleteOutlineRoundedIcon from '@mui/icons-material/DeleteOutlineRounded';
import LaunchRoundedIcon from '@mui/icons-material/LaunchRounded';
import { usePlant } from '../context/PlantContext';
import {
  getReports,
  generateReport,
  uploadCompanyLogo,
  getCompanyLogoUrl,
  deleteReport,
  downloadReportFile,
  openReport,
} from '../services/api';
import type { Report } from '../types';
import { DateFilterBar } from '../components/DateFilterBar';

export const ReportsPage: React.FC = () => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const { selectedPlantId, startDate, endDate } = usePlant();
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [generating, setGenerating] = useState<string | null>(null); // 'pdf' | 'docx' | null
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [openingId, setOpeningId] = useState<number | null>(null);
  const [downloadingId, setDownloadingId] = useState<number | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Logo branding state
  const [logoUploading, setLogoUploading] = useState(false);
  const [logoSuccess, setLogoSuccess] = useState<string | null>(null);
  const [logoKey, setLogoKey] = useState(Date.now()); // cache buster for image

  const handleDeleteReport = async (reportId: number, title: string) => {
    if (!selectedPlantId) return;
    if (!window.confirm(`Are you sure you want to permanently delete "${title}"? This cannot be undone.`)) {
      return;
    }
    try {
      setDeletingId(reportId);
      await deleteReport(selectedPlantId, reportId);
      await fetchReports();
    } catch (err: any) {
      console.error('Error deleting report:', err);
      setError(err.response?.data?.detail || 'Failed to delete report.');
    } finally {
      setDeletingId(null);
    }
  };

  const handleLogoUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!selectedPlantId || !event.target.files || event.target.files.length === 0) return;
    const file = event.target.files[0];
    try {
      setLogoUploading(true);
      setLogoSuccess(null);
      await uploadCompanyLogo(selectedPlantId, file);
      setLogoSuccess('Company logo uploaded successfully. It will now appear on all report cover pages.');
      setLogoKey(Date.now());
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload company logo.');
    } finally {
      setLogoUploading(false);
    }
  };

  const fetchReports = async () => {
    if (!selectedPlantId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await getReports(selectedPlantId);
      setReports(res);
    } catch (err) {
      console.error('Error listing reports:', err);
      setError('Failed to retrieve previously generated reports list.');
    } finally {
      setLoading(false);
    }

  };

  useEffect(() => {
    fetchReports();
  }, [selectedPlantId]);

  const handleGenerate = async (type: 'pdf' | 'docx') => {
    if (!selectedPlantId) return;
    try {
      setGenerating(type);
      setError(null);
      setActionSuccess(null);
      await generateReport(selectedPlantId, type, startDate, endDate);
      await fetchReports(); // reload list
      setActionSuccess(`${type.toUpperCase()} report generated successfully. You can open or download it below.`);
      setTimeout(() => setActionSuccess(null), 6000);
    } catch (err: any) {
      console.error('Error generating report:', err);
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : `Failed to generate ${type.toUpperCase()} report.`);
    } finally {
      setGenerating(null);
    }
  };

  const handleOpenReport = async (reportId: number) => {
    if (!selectedPlantId) return;
    try {
      setOpeningId(reportId);
      setError(null);
      const res = await openReport(selectedPlantId, reportId);
      setActionSuccess(res.message);
      setTimeout(() => setActionSuccess(null), 5000);
    } catch (err: any) {
      console.error('Error opening report:', err);
      setError(err.response?.data?.detail || 'Failed to open report in default application.');
    } finally {
      setOpeningId(null);
    }
  };

  const handleDownloadReport = async (reportId: number, filePath: string, reportType: string) => {
    if (!selectedPlantId) return;
    const parts = filePath.split(/[\\/]/);
    const filename = parts[parts.length - 1] || `report_${reportId}.${reportType}`;
    try {
      setDownloadingId(reportId);
      setError(null);
      await downloadReportFile(selectedPlantId, reportId, filename);
    } catch (err: any) {
      console.error('Error downloading report:', err);
      // Fallback: direct window open if blob download encountered an issue
      try {
        const downloadUrl = `/api/plants/${selectedPlantId}/reports/${reportId}/download`;
        window.open(downloadUrl, '_blank');
      } catch {
        setError(err.response?.data?.detail || 'Failed to download report.');
      }
    } finally {
      setDownloadingId(null);
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
      <Typography variant="h4" sx={{ fontWeight: 'bold', color: 'primary.main' }}>
        Reports & Exports
      </Typography>

      <DateFilterBar />

      {/* ─── Company Branding & Logo Customization ─── */}
      <Card
        sx={{
          background: isDark ? 'rgba(22, 27, 38, 0.7)' : '#FFFFFF',
          border: '1px solid',
          borderColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.08)',
        }}
      >
        <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <BusinessRoundedIcon color="primary" />
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Company Branding & Cover Page Logo
            </Typography>
          </Box>
          <Typography variant="body2" color="text.secondary">
            Upload your company or client logo. It will be automatically formatted and embedded onto the cover page of all generated PDF and Word reports.
          </Typography>

          {logoSuccess && <Alert severity="success">{logoSuccess}</Alert>}

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 3, flexWrap: 'wrap', mt: 1 }}>
            <Box
              sx={{
                width: 140,
                height: 60,
                border: '1px dashed',
                borderColor: 'divider',
                borderRadius: 2,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                overflow: 'hidden',
                bgcolor: isDark ? 'rgba(0, 0, 0, 0.2)' : 'rgba(0, 0, 0, 0.03)',
              }}
            >
              <img
                key={logoKey}
                src={`${getCompanyLogoUrl(selectedPlantId)}?t=${logoKey}`}
                alt="Company Logo"
                style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
                onError={(e) => {
                  (e.target as HTMLElement).style.display = 'none';
                }}
                onLoad={(e) => {
                  (e.target as HTMLElement).style.display = 'block';
                }}
              />
            </Box>

            <Button
              component="label"
              variant="outlined"
              startIcon={logoUploading ? <CircularProgress size={18} color="inherit" /> : <CloudUploadRoundedIcon />}
              disabled={logoUploading}
              sx={{ borderRadius: 2 }}
            >
              {logoUploading ? 'Uploading...' : 'Upload Company Logo'}
              <input type="file" accept="image/png, image/jpeg, image/webp" hidden onChange={handleLogoUpload} />
            </Button>
          </Box>
        </CardContent>
      </Card>

      {/* ─── Generate Reports ─── */}
      <Card
        sx={{
          background: isDark ? 'rgba(22, 27, 38, 0.7)' : '#FFFFFF',
          border: '1px solid',
          borderColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.08)',
        }}
      >
        <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>Generate Performance Report</Typography>
          <Typography variant="body2" color="text.secondary">
            Trigger generation of professional plant evaluation dossiers. Reports include cover pages, annual performance metrics, inverter generation summaries, loss breakdowns, and linear regression degradation trends.
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mt: 1 }}>
            <Button
              variant="contained"
              color="error"
              size="large"
              startIcon={generating === 'pdf' ? <CircularProgress size={20} color="inherit" /> : <PictureAsPdfRoundedIcon />}
              disabled={generating !== null}
              onClick={() => handleGenerate('pdf')}
              sx={{ px: 3, fontWeight: 700 }}
            >
              {generating === 'pdf' ? 'Generating PDF...' : 'Export PDF Document'}
            </Button>
            <Button
              variant="contained"
              color="primary"
              size="large"
              startIcon={generating === 'docx' ? <CircularProgress size={20} color="inherit" /> : <DescriptionRoundedIcon />}
              disabled={generating !== null}
              onClick={() => handleGenerate('docx')}
              sx={{ px: 3, fontWeight: 700 }}
            >
              {generating === 'docx' ? 'Generating Word...' : 'Export Word Document (.docx)'}
            </Button>
          </Box>
        </CardContent>
      </Card>

      {error && <Alert severity="error" onClose={() => setError(null)}>{error}</Alert>}
      {actionSuccess && <Alert severity="success" onClose={() => setActionSuccess(null)}>{actionSuccess}</Alert>}

      <Typography variant="h6" sx={{ fontWeight: 600 }}>Dossier Archives</Typography>

      {loading && reports.length === 0 ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 5 }}>
          <CircularProgress color="primary" />
        </Box>
      ) : reports.length > 0 ? (
        <TableContainer
          component={Paper}
          sx={{
            background: isDark ? 'rgba(22, 27, 38, 0.7)' : '#FFFFFF',
            border: '1px solid',
            borderColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.08)',
          }}
        >
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell><Typography variant="subtitle2">Report Title</Typography></TableCell>
                <TableCell><Typography variant="subtitle2">Format</Typography></TableCell>
                <TableCell><Typography variant="subtitle2">Date Generated</Typography></TableCell>
                <TableCell><Typography variant="subtitle2">Analysis Period</Typography></TableCell>
                <TableCell align="right"><Typography variant="subtitle2">Actions</Typography></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {reports.map((row) => (
                <TableRow key={row.id}>
                  <TableCell sx={{ fontWeight: 600 }}>{row.title}</TableCell>
                  <TableCell>{row.report_type.toUpperCase()}</TableCell>
                  <TableCell>{new Date(row.generated_at).toLocaleString()}</TableCell>
                  <TableCell>{row.period_start} to {row.period_end}</TableCell>
                  <TableCell align="right">
                    <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end', alignItems: 'center' }}>
                      <Button
                        variant="contained"
                        size="small"
                        color="primary"
                        startIcon={openingId === row.id ? <CircularProgress size={16} color="inherit" /> : <LaunchRoundedIcon />}
                        onClick={() => handleOpenReport(row.id)}
                        disabled={openingId === row.id}
                        sx={{ textTransform: 'none', fontWeight: 600 }}
                        title={`Open ${row.report_type.toUpperCase()} directly in desktop application`}
                      >
                        {openingId === row.id ? 'Opening...' : 'Open'}
                      </Button>
                      <Button
                        variant="outlined"
                        size="small"
                        startIcon={downloadingId === row.id ? <CircularProgress size={16} color="inherit" /> : <FileDownloadRoundedIcon />}
                        onClick={() => handleDownloadReport(row.id, row.file_path, row.report_type)}
                        disabled={downloadingId === row.id}
                        sx={{ textTransform: 'none' }}
                        title="Download report file"
                      >
                        {downloadingId === row.id ? 'Saving...' : 'Download'}
                      </Button>
                      <Button
                        variant="outlined"
                        size="small"
                        color="error"
                        startIcon={<DeleteOutlineRoundedIcon />}
                        onClick={() => handleDeleteReport(row.id, row.title)}
                        disabled={deletingId === row.id}
                        sx={{ textTransform: 'none' }}
                        title="Delete report"
                      >
                        {deletingId === row.id ? 'Deleting...' : 'Delete'}
                      </Button>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
        <Typography color="text.secondary">No reports generated yet. Click generate above to compile a performance assessment.</Typography>
      )}
    </Box>
  );
};
