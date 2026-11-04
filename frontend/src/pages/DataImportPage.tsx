import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  LinearProgress,
  Alert,
  AlertTitle,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded';
import ErrorOutlineRoundedIcon from '@mui/icons-material/ErrorOutlineRounded';
import WarningRoundedIcon from '@mui/icons-material/WarningRounded';
import InsertDriveFileRoundedIcon from '@mui/icons-material/InsertDriveFileRounded';
import { usePlant } from '../context/PlantContext';
import { importData } from '../services/api';
import type { ImportValidationResult } from '../types';

export const DataImportPage: React.FC = () => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const { selectedPlantId, refreshPlants } = usePlant();
  const [file, setFile] = useState<File | null>(null);
  const [importType, setImportType] = useState<string>('multi_sheet');
  const [uploading, setUploading] = useState<boolean>(false);
  const [progressStep, setProgressStep] = useState<string>('Uploading dataset...');
  const [result, setResult] = useState<ImportValidationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      const selected = event.target.files[0];
      setFile(selected);
      if (selected.name.toLowerCase().endsWith('.csv')) {
        setImportType('csv');
      } else if (importType === 'csv') {
        setImportType('multi_sheet');
      }
      setResult(null);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedPlantId || !file) return;

    try {
      setUploading(true);
      setError(null);
      setResult(null);
      setProgressStep('Uploading dataset to local analytics engine...');

      const stepTimer1 = setTimeout(() => {
        setProgressStep('Parsing worksheets and validating time-series records...');
      }, 600);

      const stepTimer2 = setTimeout(() => {
        setProgressStep('Computing solar PR, irradiation and inverter losses...');
      }, 1600);

      const res = await importData(selectedPlantId, file, importType);
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      setProgressStep('Validating data integrity and updating database...');
      setResult(res);

      if (res.valid_rows > 0) {
        refreshPlants();
      }
    } catch (err: any) {
      console.error('[Import] Upload failed:', err);
      setError(err.response?.data?.detail || 'An error occurred during file upload.');
    } finally {
      setUploading(false);
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
        Solar Monitoring Data Import (XLSX / CSV)
      </Typography>

      <Card
        sx={{
          background: isDark ? 'rgba(22, 27, 38, 0.7)' : '#FFFFFF',
          backdropFilter: 'blur(10px)',
          border: '1px solid',
          borderColor: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.08)',
        }}
      >
        <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Upload Plant Dataset (Multi-sheet XLSX, Single-sheet, or SCADA CSV)
          </Typography>

          <FormControl component="fieldset">
            <FormLabel component="legend" sx={{ mb: 1, color: 'text.secondary' }}>Import Format Mode</FormLabel>
            <RadioGroup row value={importType} onChange={(e) => setImportType(e.target.value)}>
              <FormControlLabel value="multi_sheet" control={<Radio />} label="Inverter sheets (Multi-sheet XLSX)" />
              <FormControlLabel value="single_sheet" control={<Radio />} label="Aggregated (Single sheet XLSX)" />
              <FormControlLabel value="csv" control={<Radio />} label="SCADA Log (CSV format)" />
            </RadioGroup>
          </FormControl>

          <Box
            sx={{
              border: '2px dashed',
              borderColor: isDark ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.2)',
              borderRadius: 2,
              p: 4,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              bgcolor: isDark ? 'rgba(0, 0, 0, 0.2)' : 'rgba(0, 0, 0, 0.02)',
            }}
          >
            <CloudUploadIcon sx={{ fontSize: 50, color: 'primary.main', mb: 2 }} />
            <Button component="label" variant="contained" sx={{ mb: 2 }}>
              Choose Dataset File
              <input type="file" accept=".xlsx, .xls, .csv" hidden onChange={handleFileChange} />
            </Button>
            {file ? (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <InsertDriveFileRoundedIcon color="primary" />
                <Typography variant="body2" color="primary.main" sx={{ fontWeight: 600 }}>
                  Selected: {file.name} ({(file.size / 1024).toFixed(1)} KB)
                </Typography>
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary">
                Drag and drop your XLSX spreadsheet or CSV log here or click Browse
              </Typography>
            )}
          </Box>

          <Button
            variant="contained"
            color="primary"
            size="large"
            disabled={!file || uploading}
            onClick={handleUpload}
            sx={{ alignSelf: 'flex-start', px: 4, fontWeight: 700 }}
          >
            {uploading ? 'Processing Dataset...' : 'Upload & Parse Dataset'}
          </Button>

          {uploading && (
            <Box sx={{ width: '100%', mt: 1 }}>
              <LinearProgress sx={{ borderRadius: 1, height: 6 }} />
              <Typography variant="caption" color="primary.main" sx={{ mt: 1.5, display: 'block', fontWeight: 600 }}>
                {progressStep}
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>


      {error && (
        <Alert severity="error">
          <AlertTitle>Import Failed</AlertTitle>
          {error}
        </Alert>
      )}

      {result && (
        <Card sx={{ background: 'rgba(255, 255, 255, 0.05)', backdropFilter: 'blur(10px)', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
          <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              {result.is_valid ? (
                <CheckCircleRoundedIcon sx={{ color: 'success.main', fontSize: 40 }} />
              ) : result.valid_rows > 0 ? (
                <WarningRoundedIcon sx={{ color: 'warning.main', fontSize: 40 }} />
              ) : (
                <ErrorOutlineRoundedIcon sx={{ color: 'error.main', fontSize: 40 }} />
              )}
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  {result.is_valid ? 'Import Successful' : result.valid_rows > 0 ? 'Imported with Errors' : 'Import Failed'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Processed {result.total_rows} total data rows, {result.valid_rows} valid records loaded.
                </Typography>
              </Box>
            </Box>

            {result.warnings.length > 0 && (
              <Alert severity="warning">
                <AlertTitle>Warnings Detected</AlertTitle>
                <Box component="ul" sx={{ m: 0, pl: 2 }}>
                  {result.warnings.map((w, i) => (
                    <li key={i}><Typography variant="body2">{w}</Typography></li>
                  ))}
                </Box>
              </Alert>
            )}

            {!result.is_valid && result.errors.length > 0 && (
              <Box>
                <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1, color: 'error.main' }}>
                  Syntax & Constraint Errors Found:
                </Typography>
                <TableContainer component={Paper} sx={{ bgcolor: 'rgba(0, 0, 0, 0.3)', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell><Typography variant="subtitle2">Row</Typography></TableCell>
                        <TableCell><Typography variant="subtitle2">Column</Typography></TableCell>
                        <TableCell><Typography variant="subtitle2">Error Message</Typography></TableCell>
                        <TableCell><Typography variant="subtitle2">Invalid Value</Typography></TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {result.errors.map((err, i) => (
                        <TableRow key={i}>
                          <TableCell>{err.row}</TableCell>
                          <TableCell>{err.column}</TableCell>
                          <TableCell color="error">{err.message}</TableCell>
                          <TableCell sx={{ fontFamily: 'monospace' }}>{err.value}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Box>
            )}
          </CardContent>
        </Card>
      )}
    </Box>
  );
};
