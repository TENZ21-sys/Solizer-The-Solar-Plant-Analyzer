import React, { useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Tabs,
  Tab,
  TextField,
  Button,
  Switch,
  FormControlLabel,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
  Alert,
  Divider,
  Paper,
  InputAdornment,
} from '@mui/material';
import Grid from '@mui/material/Grid';
import { useTheme } from '@mui/material/styles';
import PersonRoundedIcon from '@mui/icons-material/PersonRounded';
import TuneRoundedIcon from '@mui/icons-material/TuneRounded';
import SpeedRoundedIcon from '@mui/icons-material/SpeedRounded';
import AttachMoneyRoundedIcon from '@mui/icons-material/AttachMoneyRounded';
import StorageRoundedIcon from '@mui/icons-material/StorageRounded';
import SaveRoundedIcon from '@mui/icons-material/SaveRounded';
import DownloadRoundedIcon from '@mui/icons-material/DownloadRounded';
import CachedRoundedIcon from '@mui/icons-material/CachedRounded';
import CloudUploadRoundedIcon from '@mui/icons-material/CloudUploadRounded';
import InfoRoundedIcon from '@mui/icons-material/InfoRounded';

import { usePlant } from '../context/PlantContext';
import {
  getSettings,
  updateSettings,
  getSystemStats,
  getDatabaseBackupUrl,
  optimizeDatabase,
  clearSystemCache,
  uploadCompanyLogo,
  getCompanyLogoUrl,
  type SystemStats,
} from '../services/api';

const CURRENCIES = [
  { code: 'USD', symbol: '$', label: 'USD ($) - US Dollar' },
  { code: 'EUR', symbol: '€', label: 'EUR (€) - Euro' },
  { code: 'LKR', symbol: 'Rs.', label: 'LKR (Rs.) - Sri Lankan Rupee' },
  { code: 'GBP', symbol: '£', label: 'GBP (£) - British Pound' },
  { code: 'INR', symbol: '₹', label: 'INR (₹) - Indian Rupee' },
  { code: 'AUD', symbol: 'A$', label: 'AUD (A$) - Australian Dollar' },
];

export const SettingsPage: React.FC = () => {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';
  const { selectedPlantId } = usePlant();

  const [currentTab, setCurrentTab] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Settings State
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [stats, setStats] = useState<SystemStats | null>(null);

  // Logo upload state
  const [logoUploading, setLogoUploading] = useState(false);
  const [logoKey, setLogoKey] = useState(Date.now());

  const fetchAllData = async () => {
    try {
      setLoading(true);
      const [settingsRes, statsRes] = await Promise.all([
        getSettings(),
        getSystemStats(),
      ]);
      setSettings(settingsRes.settings || {});
      setStats(statsRes);
    } catch (err: any) {
      console.error('Failed to load settings:', err);
      setFeedback({ type: 'error', message: 'Could not load configuration settings.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
  }, []);

  const handleChange = (key: string, value: string) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  const handleToggle = (key: string) => {
    setSettings((prev) => ({
      ...prev,
      [key]: prev[key] === 'false' ? 'true' : 'false',
    }));
  };

  const handleCurrencyChange = (code: string) => {
    const selected = CURRENCIES.find((c) => c.code === code);
    if (selected) {
      setSettings((prev) => ({
        ...prev,
        currency_code: selected.code,
        currency_symbol: selected.symbol,
      }));
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setFeedback(null);
      await updateSettings(settings);
      setFeedback({ type: 'success', message: 'Configuration saved successfully! All views and reports have been updated.' });
      // Notify layout and other components
      window.dispatchEvent(new CustomEvent('settingsUpdated', { detail: settings }));
    } catch (err: any) {
      console.error('Failed to save settings:', err);
      setFeedback({ type: 'error', message: err.response?.data?.detail || 'Failed to save settings.' });
    } finally {
      setSaving(false);
    }
  };

  const [optimizing, setOptimizing] = useState(false);
  const [downloadingBackup, setDownloadingBackup] = useState(false);

  const handleOptimizeDb = async () => {
    try {
      setOptimizing(true);
      const res = await optimizeDatabase();
      setFeedback({ type: res.success ? 'success' : 'error', message: res.message });
      await fetchAllData();
    } catch (err: any) {
      console.error('Failed to optimize database:', err);
      setFeedback({ type: 'error', message: 'Failed to optimize database.' });
    } finally {
      setOptimizing(false);
    }
  };

  const handleDownloadBackup = async () => {
    try {
      setDownloadingBackup(true);
      setFeedback({ type: 'success', message: 'Generating fresh database backup...' });
      const backupUrl = getDatabaseBackupUrl();
      const res = await fetch(backupUrl);
      if (!res.ok) throw new Error('Backup request failed');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `solizer_backup_${new Date().toISOString().slice(0, 10)}.db`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setFeedback({ type: 'success', message: 'Database backup downloaded successfully.' });
    } catch (err: any) {
      console.error('Failed to download backup:', err);
      setFeedback({ type: 'error', message: 'Failed to download database backup.' });
    } finally {
      setDownloadingBackup(false);
    }
  };

  const handleClearCache = async () => {
    try {
      const res = await clearSystemCache();
      setFeedback({ type: 'success', message: res.message || 'System cache cleared.' });
      await fetchAllData();
    } catch (err: any) {
      setFeedback({ type: 'error', message: 'Failed to clear cache.' });
    }
  };

  const handleLogoUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!selectedPlantId || !event.target.files || event.target.files.length === 0) return;
    const file = event.target.files[0];
    try {
      setLogoUploading(true);
      await uploadCompanyLogo(selectedPlantId, file);
      setLogoKey(Date.now());
      setFeedback({ type: 'success', message: 'Company logo uploaded and updated successfully!' });
    } catch (err: any) {
      setFeedback({ type: 'error', message: 'Failed to upload company logo.' });
    } finally {
      setLogoUploading(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <CircularProgress color="primary" />
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, maxWidth: 1200, mx: 'auto', pb: 6 }}>
      {/* Page Title & Save Action */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, color: 'primary.main' }}>
            Settings & System Preferences
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Manage auditor identity, navigation modules, IEC engineering thresholds, currency, and data backups.
          </Typography>
        </Box>
        <Button
          variant="contained"
          color="primary"
          size="large"
          startIcon={saving ? <CircularProgress size={18} color="inherit" /> : <SaveRoundedIcon />}
          disabled={saving}
          onClick={handleSave}
          sx={{ borderRadius: 2, fontWeight: 700, px: 3 }}
        >
          {saving ? 'Saving Changes...' : 'Save Settings'}
        </Button>
      </Box>

      {feedback && (
        <Alert severity={feedback.type} onClose={() => setFeedback(null)}>
          {feedback.message}
        </Alert>
      )}

      {/* Tabs Bar */}
      <Paper
        elevation={0}
        sx={{
          borderRadius: 3,
          border: '1px solid',
          borderColor: 'divider',
          bgcolor: isDark ? 'rgba(22, 27, 38, 0.7)' : '#FFFFFF',
        }}
      >
        <Tabs
          value={currentTab}
          onChange={(_, val) => setCurrentTab(val)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{
            px: 2,
            '& .MuiTab-root': {
              minHeight: 56,
              fontWeight: 700,
              fontSize: '0.9rem',
              gap: 1,
            },
          }}
        >
          <Tab icon={<PersonRoundedIcon />} iconPosition="start" label="Auditor Profile" />
          <Tab icon={<TuneRoundedIcon />} iconPosition="start" label="Modules & Navigation" />
          <Tab icon={<SpeedRoundedIcon />} iconPosition="start" label="Thresholds & IEC" />
          <Tab icon={<AttachMoneyRoundedIcon />} iconPosition="start" label="Economics & Currency" />
          <Tab icon={<StorageRoundedIcon />} iconPosition="start" label="Data Safety & Maintenance" />
        </Tabs>
      </Paper>

      {/* ─── TAB 0: Auditor Profile ─── */}
      {currentTab === 0 && (
        <Card sx={{ borderRadius: 3, border: '1px solid', borderColor: 'divider' }}>
          <CardContent sx={{ p: 4, display: 'flex', flexDirection: 'column', gap: 3 }}>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                Auditor & Engineering Credentials
              </Typography>
              <Typography variant="body2" color="text.secondary">
                These credentials dynamically populate the "Prepared by" metadata on cover pages and executive briefing cards across all PDF and Word reports.
              </Typography>
            </Box>

            <Grid container spacing={3}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth
                  label="Lead Auditor Name"
                  value={settings.auditor_name || ''}
                  onChange={(e) => handleChange('auditor_name', e.target.value)}
                  placeholder="e.g. Akalanka"
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth
                  label="Engineering Firm / Organization"
                  value={settings.organization || ''}
                  onChange={(e) => handleChange('organization', e.target.value)}
                  placeholder="e.g. Solar Intelligence Engineering"
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth
                  label="Auditor Email Address"
                  value={settings.email || ''}
                  onChange={(e) => handleChange('email', e.target.value)}
                  placeholder="e.g. auditor@solizer.com"
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth
                  label="Professional Designation"
                  value={settings.designation || ''}
                  onChange={(e) => handleChange('designation', e.target.value)}
                  placeholder="e.g. Lead Solar Asset Auditor"
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth
                  label="Accreditation / License ID"
                  value={settings.license_id || ''}
                  onChange={(e) => handleChange('license_id', e.target.value)}
                  placeholder="e.g. PV-ENG-49201"
                />
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* ─── TAB 1: Modules & Navigation ─── */}
      {currentTab === 1 && (
        <Card sx={{ borderRadius: 3, border: '1px solid', borderColor: 'divider' }}>
          <CardContent sx={{ p: 4, display: 'flex', flexDirection: 'column', gap: 4 }}>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                Sidebar Navigation & Module Enablement
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Turn modules on or off according to plant needs. Disabled modules are hidden from the sidebar navigation.
              </Typography>
            </Box>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.enabled_inverters !== 'false'}
                    onChange={() => handleToggle('enabled_inverters')}
                    color="primary"
                  />
                }
                label={
                  <Box>
                    <Typography sx={{ fontWeight: 600 }}>Inverter-Level Performance Analysis</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Enables individual inverter PR, specific yield, and block generation comparison tables and graphs.
                    </Typography>
                  </Box>
                }
              />
              <Divider />

              <FormControlLabel
                control={
                  <Switch
                    checked={settings.enabled_losses !== 'false'}
                    onChange={() => handleToggle('enabled_losses')}
                    color="primary"
                  />
                }
                label={
                  <Box>
                    <Typography sx={{ fontWeight: 600 }}>Energy Loss Breakdown Module</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Computes grid failure, curtailment, and machine downtime energy losses and stacked charts.
                    </Typography>
                  </Box>
                }
              />
              <Divider />

              <FormControlLabel
                control={
                  <Switch
                    checked={settings.enabled_degradation !== 'false'}
                    onChange={() => handleToggle('enabled_degradation')}
                    color="primary"
                  />
                }
                label={
                  <Box>
                    <Typography sx={{ fontWeight: 600 }}>Degradation & PV Aging Analytics</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Tracks annualized PR degradation slope against manufacturer nameplate degradation warranty.
                    </Typography>
                  </Box>
                }
              />
              <Divider />

              <FormControlLabel
                control={
                  <Switch
                    checked={settings.enabled_irradiation !== 'false'}
                    onChange={() => handleToggle('enabled_irradiation')}
                    color="primary"
                  />
                }
                label={
                  <Box>
                    <Typography sx={{ fontWeight: 600 }}>Solar Irradiation & Pyranometer Tracking</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Analyzes on-site solar insolation, pyranometer fidelity, and specific yield correlation.
                    </Typography>
                  </Box>
                }
              />
              <Divider />

              <FormControlLabel
                control={
                  <Switch
                    checked={settings.enabled_alerts !== 'false'}
                    onChange={() => handleToggle('enabled_alerts')}
                    color="primary"
                  />
                }
                label={
                  <Box>
                    <Typography sx={{ fontWeight: 600 }}>Operational Alerts & Anomalies</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Automated flagging of underperforming inverters, grid curtailment events, and soiling alerts.
                    </Typography>
                  </Box>
                }
              />
            </Box>

            <Box sx={{ mt: 2 }}>
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>
                Report Chapter Customization
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Control which major sections are included when generating PDF and Word dossiers.
              </Typography>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.report_include_exec_summary !== 'false'}
                        onChange={() => handleToggle('report_include_exec_summary')}
                      />
                    }
                    label="Executive Summary & KPI Deck (Page 2)"
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.report_include_kpi_analysis !== 'false'}
                        onChange={() => handleToggle('report_include_kpi_analysis')}
                      />
                    }
                    label="Plant-Level Annual Performance Table & Charts"
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.report_include_inverters !== 'false'}
                        onChange={() => handleToggle('report_include_inverters')}
                      />
                    }
                    label="Inverter Fleet Comparison & Block Tables"
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.report_include_losses !== 'false'}
                        onChange={() => handleToggle('report_include_losses')}
                      />
                    }
                    label="Loss Analysis (Grid, Curtailment, Machine)"
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.report_include_recommendations !== 'false'}
                        onChange={() => handleToggle('report_include_recommendations')}
                      />
                    }
                    label="Actionable Recommendations & Next Steps"
                  />
                </Grid>
              </Grid>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* ─── TAB 2: Thresholds & IEC Calibration ─── */}
      {currentTab === 2 && (
        <Card sx={{ borderRadius: 3, border: '1px solid', borderColor: 'divider' }}>
          <CardContent sx={{ p: 4, display: 'flex', flexDirection: 'column', gap: 3 }}>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                Engineering Thresholds & IEC 61724 Calibration
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Define the mathematical boundaries for automated alert detection and temperature-corrected PR calculation.
              </Typography>
            </Box>

            <Grid container spacing={3}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth
                  type="number"
                  label="Performance Ratio (PR) Alert Floor"
                  value={settings.pr_alert_threshold || '75.0'}
                  onChange={(e) => handleChange('pr_alert_threshold', e.target.value)}
                  slotProps={{
                    input: { endAdornment: <InputAdornment position="end">%</InputAdornment> },
                  }}
                  helperText="Performance below this threshold triggers critical operational alerts."
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth
                  type="number"
                  label="Inverter Discrepancy Tolerance"
                  value={settings.inverter_discrepancy_threshold || '5.0'}
                  onChange={(e) => handleChange('inverter_discrepancy_threshold', e.target.value)}
                  slotProps={{
                    input: { endAdornment: <InputAdornment position="end">%</InputAdornment> },
                  }}
                  helperText="Tolerance between top and bottom inverter PR before raising a discrepancy flag."
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth
                  type="number"
                  label="CUF (Capacity Utilisation Factor) Floor"
                  value={settings.cuf_threshold || '15.0'}
                  onChange={(e) => handleChange('cuf_threshold', e.target.value)}
                  slotProps={{
                    input: { endAdornment: <InputAdornment position="end">%</InputAdornment> },
                  }}
                  helperText="Minimum expected annualized CUF for grid availability compliance."
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth
                  label="IEC 61724 Power Temperature Coefficient (γ)"
                  value={settings.temp_coefficient || '-0.0040'}
                  onChange={(e) => handleChange('temp_coefficient', e.target.value)}
                  slotProps={{
                    input: { endAdornment: <InputAdornment position="end">/ °C</InputAdornment> },
                  }}
                  helperText="Typically -0.0040 / °C (-0.40%/°C) for standard silicon PV modules."
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth
                  type="number"
                  label="Reference Cell Temperature (STC)"
                  value={settings.reference_cell_temp || '25.0'}
                  onChange={(e) => handleChange('reference_cell_temp', e.target.value)}
                  slotProps={{
                    input: { endAdornment: <InputAdornment position="end">°C</InputAdornment> },
                  }}
                  helperText="Standard STC reference cell temperature (IEC standard is 25.0 °C)."
                />
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* ─── TAB 3: Economics & Currency ─── */}
      {currentTab === 3 && (
        <Card sx={{ borderRadius: 3, border: '1px solid', borderColor: 'divider' }}>
          <CardContent sx={{ p: 4, display: 'flex', flexDirection: 'column', gap: 3 }}>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                Financial Revenue Loss & Multi-Currency Economics
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Configure currency display, tariff monetization, legal disclaimers, and custom client branding.
              </Typography>
            </Box>

            <Grid container spacing={3}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <FormControl fullWidth>
                  <InputLabel id="currency-select-label">Multi-Currency Format</InputLabel>
                  <Select
                    labelId="currency-select-label"
                    value={settings.currency_code || 'USD'}
                    label="Multi-Currency Format"
                    onChange={(e) => handleCurrencyChange(e.target.value)}
                  >
                    {CURRENCIES.map((c) => (
                      <MenuItem key={c.code} value={c.code}>
                        {c.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth
                  type="number"
                  label="Grid Feed-in Tariff Rate (per kWh)"
                  value={settings.tariff_rate || '0.12'}
                  onChange={(e) => handleChange('tariff_rate', e.target.value)}
                  slotProps={{
                    input: {
                      startAdornment: (
                        <InputAdornment position="start">{settings.currency_symbol || '$'}</InputAdornment>
                      ),
                      endAdornment: <InputAdornment position="end">/ kWh</InputAdornment>,
                    },
                  }}
                  helperText="Monetizes grid failure, curtailment, and machine downtime energy losses."
                />
              </Grid>

              <Grid size={{ xs: 12 }}>
                <TextField
                  fullWidth
                  multiline
                  rows={3}
                  label="Regulatory Compliance & Audit Disclaimer"
                  value={settings.report_disclaimer || ''}
                  onChange={(e) => handleChange('report_disclaimer', e.target.value)}
                  helperText="Appears at the conclusion of all generated report documents."
                />
              </Grid>

              <Grid size={{ xs: 12 }}>
                <Divider sx={{ my: 1 }} />
                <Typography variant="subtitle1" sx={{ fontWeight: 700, mt: 1, mb: 1 }}>
                  Plant / Organization Logo Customization
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Upload a high-resolution logo for cover page header embedding.
                </Typography>

                <Box sx={{ display: 'flex', alignItems: 'center', gap: 3, flexWrap: 'wrap' }}>
                  {selectedPlantId && (
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
                        alt="Current Logo"
                        style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = 'none';
                        }}
                        onLoad={(e) => {
                          (e.target as HTMLElement).style.display = 'block';
                        }}
                      />
                    </Box>
                  )}

                  <Button
                    component="label"
                    variant="outlined"
                    startIcon={logoUploading ? <CircularProgress size={18} color="inherit" /> : <CloudUploadRoundedIcon />}
                    disabled={logoUploading || !selectedPlantId}
                  >
                    {logoUploading ? 'Uploading...' : 'Upload New Logo'}
                    <input type="file" accept="image/png, image/jpeg, image/webp" hidden onChange={handleLogoUpload} />
                  </Button>
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* ─── TAB 4: Data Safety & System Maintenance ─── */}
      {currentTab === 4 && (
        <Card sx={{ borderRadius: 3, border: '1px solid', borderColor: 'divider' }}>
          <CardContent sx={{ p: 4, display: 'flex', flexDirection: 'column', gap: 3 }}>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                Data Safety, Correction & System Maintenance
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Review storage footprint, download single-file database backups, and manage mistaken inputs.
              </Typography>
            </Box>

            {/* Safe Mistake Correction Guide */}
            <Alert icon={<InfoRoundedIcon />} severity="info" sx={{ borderRadius: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                Data Entry & Mistake-Correction Safety
              </Typography>
              <Typography variant="body2">
                • <b>Mistakenly Entered Daily Logs:</b> You can inspect and delete any daily log via the <b>Dashboard &gt; Add Daily Log &gt; Manage &amp; Delete Logs</b> tab.<br />
                • <b>Mistakenly Generated Reports:</b> You can permanently delete any generated dossier in <b>Reports &gt; Dossier Archives</b> with the red Delete button.<br />
                • <b>Full Plant Reset:</b> You can re-edit plant specifications anytime from the <b>Plant Profile</b> page.
              </Typography>
            </Alert>

            {/* Storage Stats Cards */}
            {stats && (
              <Grid container spacing={2}>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <Paper sx={{ p: 2, textAlign: 'center', borderRadius: 2, border: '1px solid', borderColor: 'divider' }}>
                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
                      DATABASE SIZE
                    </Typography>
                    <Typography variant="h5" sx={{ fontWeight: 800, color: 'primary.main', mt: 0.5 }}>
                      {(stats.db_size_mb ?? (stats.db_size_bytes ? stats.db_size_bytes / (1024 * 1024) : (stats.database_size_kb ? stats.database_size_kb / 1024 : 0))).toFixed(2)} MB
                    </Typography>
                  </Paper>
                </Grid>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <Paper sx={{ p: 2, textAlign: 'center', borderRadius: 2, border: '1px solid', borderColor: 'divider' }}>
                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
                      POWER PLANTS
                    </Typography>
                    <Typography variant="h5" sx={{ fontWeight: 800, color: 'primary.main', mt: 0.5 }}>
                      {stats.total_plants ?? 0}
                    </Typography>
                  </Paper>
                </Grid>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <Paper sx={{ p: 2, textAlign: 'center', borderRadius: 2, border: '1px solid', borderColor: 'divider' }}>
                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
                      DAILY RECORDS
                    </Typography>
                    <Typography variant="h5" sx={{ fontWeight: 800, color: 'primary.main', mt: 0.5 }}>
                      {(stats.total_records ?? stats.total_daily_records ?? 0).toLocaleString()}
                    </Typography>
                  </Paper>
                </Grid>
                <Grid size={{ xs: 6, sm: 3 }}>
                  <Paper sx={{ p: 2, textAlign: 'center', borderRadius: 2, border: '1px solid', borderColor: 'divider' }}>
                    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 700 }}>
                      GENERATED DOSSIERS
                    </Typography>
                    <Typography variant="h5" sx={{ fontWeight: 800, color: 'primary.main', mt: 0.5 }}>
                      {stats.total_reports ?? 0}
                    </Typography>
                  </Paper>
                </Grid>
              </Grid>
            )}

            <Divider sx={{ my: 1 }} />

            {/* Backup & Maintenance Actions */}
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                1-Click Backup & Database Maintenance
              </Typography>

              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                <Button
                  variant="outlined"
                  color="primary"
                  size="large"
                  startIcon={downloadingBackup ? <CircularProgress size={18} color="inherit" /> : <DownloadRoundedIcon />}
                  onClick={handleDownloadBackup}
                  disabled={downloadingBackup}
                  sx={{ borderRadius: 2, fontWeight: 700 }}
                >
                  {downloadingBackup ? 'Preparing Backup...' : 'Download Database Backup (.db)'}
                </Button>

                <Button
                  variant="contained"
                  color="primary"
                  size="large"
                  startIcon={optimizing ? <CircularProgress size={18} color="inherit" /> : <SpeedRoundedIcon />}
                  onClick={handleOptimizeDb}
                  disabled={optimizing}
                  sx={{ borderRadius: 2, fontWeight: 700 }}
                >
                  {optimizing ? 'Optimizing Database...' : 'Optimize & Defrag Database'}
                </Button>

                <Button
                  variant="outlined"
                  color="secondary"
                  size="large"
                  startIcon={<CachedRoundedIcon />}
                  onClick={handleClearCache}
                  sx={{ borderRadius: 2, fontWeight: 700 }}
                >
                  Clear System Cache
                </Button>
              </Box>

              {(stats?.reports_dir || stats?.reports_folder) && (
                <Typography variant="caption" color="text.secondary">
                  Local Report Storage Path: <code>{stats.reports_dir || stats.reports_folder}</code>
                </Typography>
              )}
            </Box>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default SettingsPage;
