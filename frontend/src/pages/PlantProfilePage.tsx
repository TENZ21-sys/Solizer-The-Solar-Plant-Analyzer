import React, { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Stepper,
  Step,
  StepLabel,
  TextField,
  
  
  
  
  Switch,
  FormControlLabel,
  Card,
  CardContent,
  IconButton,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
} from '@mui/material';
import Grid from '@mui/material/Grid';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import AddCircleIcon from '@mui/icons-material/AddCircle';
import SettingsInputComponentIcon from '@mui/icons-material/SettingsInputComponent';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import BoltIcon from '@mui/icons-material/Bolt';

import { usePlant } from '../context/PlantContext';
import { createPlant, deletePlant, updatePlant } from '../services/api';
import type { PlantCreate, PlantUpdate } from '../types';

const STEPS = ['General Info', 'Technical Specifications', 'Operation & Expectations'];


export const PlantProfilePage: React.FC = () => {
  const { plants, selectedPlantId, setSelectedPlantId, refreshPlants } = usePlant();
  
  // Wizard state
  const [wizardOpen, setWizardOpen] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  
  // Form values state
  const [formData, setFormData] = useState<PlantCreate>({
    name: '',
    location: '',
    country: '',
    installed_dc_capacity_mw: 10.0,
    installed_ac_capacity_mw: 8.5,
    commission_date: new Date().toISOString().split('T')[0],
    number_of_blocks: 1,
      inverter_type: 'central',
      number_of_inverters: 1,
    panel_manufacturer: '',
    panel_model: '',
    total_panel_area_sqm: 50000,
    module_efficiency: 21.0,
    daily_running_hours: 5.5,
    annual_degradation_rate: 0.5,
    expected_pr: 78.0,
    expected_cuf: 18.5,
    expected_availability: 98.0,
    grid_operator: '',
    timezone: 'UTC',
    has_weather_station: false,
    has_string_monitoring: false,
    notes: '',
  });



  // Edit plant specifications state
  const [editOpen, setEditOpen] = useState(false);
  const [editingPlantId, setEditingPlantId] = useState<number | null>(null);
  const [editFormData, setEditFormData] = useState<PlantUpdate>({});


  const handleTextChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleNumberChange = (name: string, value: string) => {
    const parsed = value === '' ? 0 : parseFloat(value);
    setFormData((prev) => ({
      ...prev,
      [name]: parsed,
    }));
  };

  const handleSelectChange = (name: string, value: any) => {
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleNext = () => {
    setActiveStep((prev) => prev + 1);
  };

  const handleBack = () => {
    setActiveStep((prev) => prev - 1);
  };

  const handleOpenWizard = () => {
    setFormData({
      name: '',
      location: '',
      country: '',
      installed_dc_capacity_mw: 10.0,
      installed_ac_capacity_mw: 8.5,
      commission_date: new Date().toISOString().split('T')[0],
      number_of_blocks: 1,
      inverter_type: 'central',
      number_of_inverters: 1,
      panel_manufacturer: '',
      panel_model: '',
      total_panel_area_sqm: 50000,
      module_efficiency: 21.0,
      daily_running_hours: 5.5,
      annual_degradation_rate: 0.5,
      expected_pr: 78.0,
      expected_cuf: 18.5,
      expected_availability: 98.0,
      grid_operator: '',
      timezone: 'UTC',
      has_weather_station: false,
      has_string_monitoring: false,
      notes: '',
    });
    setActiveStep(0);
    setWizardOpen(true);
  };

  const handleSavePlant = async () => {
    try {
      const saved = await createPlant(formData);
      await refreshPlants();
      setSelectedPlantId(saved.id);
      setWizardOpen(false);
    } catch (err) {
      console.error('Error saving plant:', err);
      alert('Failed to save solar plant configuration.');
    }
  };

  const handleDeletePlant = async (id: number) => {
    if (window.confirm('WARNING: Deleting this solar plant will permanently delete ALL associated inverter records, alerts, recommendations, and report files. This cannot be undone. Proceed?')) {
      try {
        await deletePlant(id);
        await refreshPlants();
      } catch (err) {
        console.error('Error deleting plant:', err);
      }
    }
  };

  const handleOpenEdit = (plant: any) => {
    setEditingPlantId(plant.id);
    setEditFormData({
      name: plant.name,
      location: plant.location,
      country: plant.country,
      installed_dc_capacity_mw: plant.installed_dc_capacity_mw,
      installed_ac_capacity_mw: plant.installed_ac_capacity_mw,
      commission_date: plant.commission_date,
      number_of_blocks: plant.number_of_blocks,
      inverter_type: plant.inverter_type,
      number_of_inverters: plant.number_of_inverters,
      panel_manufacturer: plant.panel_manufacturer,
      panel_model: plant.panel_model,
      total_panel_area_sqm: plant.total_panel_area_sqm,
      module_efficiency: plant.module_efficiency,
      daily_running_hours: plant.daily_running_hours,
      annual_degradation_rate: plant.annual_degradation_rate,
      expected_pr: plant.expected_pr,
      expected_cuf: plant.expected_cuf,
      expected_availability: plant.expected_availability,
      grid_operator: plant.grid_operator,
      timezone: plant.timezone,
      has_weather_station: plant.has_weather_station,
      has_string_monitoring: plant.has_string_monitoring,
      notes: plant.notes || '',
    });
    setEditOpen(true);
  };

  const handleEditFieldChange = (field: keyof PlantUpdate, value: any) => {
    setEditFormData((prev: PlantUpdate) => ({
      ...prev,
      [field]: value,
    }));
  };


  const handleSavePlantEdit = async () => {
    if (editingPlantId === null) return;
    try {
      await updatePlant(editingPlantId, editFormData);
      await refreshPlants();
      setEditOpen(false);
    } catch (err) {
      console.error('Error updating plant specifications:', err);
      alert('Failed to update plant specifications.');
    }
  };


  // Validation checks for wizard steps
  const isStep1Valid = 
    formData.name.trim() !== '' &&
    formData.location.trim() !== '' &&
    formData.country.trim() !== '' &&
    formData.grid_operator.trim() !== '' &&
    formData.timezone.trim() !== '';

  const isStep2Valid = 
    formData.installed_dc_capacity_mw > 0 &&
    formData.installed_ac_capacity_mw > 0 &&
    formData.total_panel_area_sqm > 0 &&
    
    formData.panel_manufacturer.trim() !== '' &&
    formData.panel_model.trim() !== '';

  const isStep3Valid = 
    formData.module_efficiency > 0 && formData.module_efficiency <= 100 &&
    formData.daily_running_hours > 0 && formData.daily_running_hours <= 24 &&
    formData.annual_degradation_rate >= 0 && formData.annual_degradation_rate <= 100 &&
    formData.expected_pr > 0 && formData.expected_pr <= 100 &&
    formData.expected_cuf > 0 && formData.expected_cuf <= 100 &&
    formData.expected_availability > 0 && formData.expected_availability <= 100;

  const isNextDisabled = activeStep === 0 ? !isStep1Valid : (activeStep === 1 ? !isStep2Valid : !isStep3Valid);

  
  return (
    <Box>
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, letterSpacing: '-0.02em', mb: 0.5 }}>
            Plant Profiles
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Manage your registered solar installations and adjust calculation parameters.
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<AddCircleIcon />} onClick={handleOpenWizard}>
          Add Solar Plant
        </Button>
      </Box>

      {/* ─── Plant List Grid ─── */}
      <Grid container spacing={3}>
        {plants.map((plant: any) => (
          <Grid size={{ xs: 12, md: 6 }} key={plant.id}>
            <Card
              sx={{
                border: selectedPlantId === plant.id ? '2px solid' : '1px solid',
                borderColor: selectedPlantId === plant.id ? 'primary.main' : 'divider',
                position: 'relative',
              }}
            >
              <CardContent sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                  <Box>
                    <Typography variant="h6" sx={{ fontWeight: 700 }}>
                      {plant.name}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, color: 'text.secondary', mt: 0.5 }}>
                      <LocationOnIcon sx={{ fontSize: '0.9rem' }} />
                      <Typography variant="body2">{plant.location}, {plant.country}</Typography>
                    </Box>
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <IconButton size="small" onClick={() => handleOpenEdit(plant)} title="Edit Constants">
                      <EditIcon />
                    </IconButton>
                    <IconButton size="small" onClick={() => handleDeletePlant(plant.id)} title="Delete Plant" color="error">
                      <DeleteIcon />
                    </IconButton>
                  </Box>
                </Box>

                <Divider sx={{ my: 2 }} />

                <Grid container spacing={2} sx={{ mb: 2 }}>
                  <Grid size={{ xs: 6 }}>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                      DC Capacity
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <BoltIcon color="warning" sx={{ fontSize: '1.1rem' }} />
                      <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                        {plant.installed_dc_capacity_mw} MWp
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid size={{ xs: 6 }}>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                      Inverter Count
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <SettingsInputComponentIcon color="primary" sx={{ fontSize: '1.1rem' }} />
                      <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                        {plant.number_of_inverters} ({plant.inverter_type})
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid size={{ xs: 6 }}>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                      Commission Date
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <CalendarMonthIcon color="action" sx={{ fontSize: '1.1rem' }} />
                      <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                        {new Date(plant.commission_date).toLocaleDateString()}
                      </Typography>
                    </Box>
                  </Grid>
                  <Grid size={{ xs: 6 }}>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                      Module Efficiency
                    </Typography>
                    <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                      {plant.module_efficiency}%
                    </Typography>
                  </Grid>
                </Grid>

                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Chip
                      size="small"
                      label={`Running: ${plant.daily_running_hours}h`}
                      variant="outlined"
                    />
                    {plant.has_weather_station && (
                      <Chip
                        size="small"
                        label="Weather Stn"
                        color="success"
                        variant="outlined"
                      />
                    )}
                    {plant.has_string_monitoring && (
                      <Chip
                        size="small"
                        label="String Monit."
                        color="info"
                        variant="outlined"
                      />
                    )}
                  </Box>
                  {selectedPlantId !== plant.id && (
                    <Button size="small" variant="text" onClick={() => setSelectedPlantId(plant.id)}>
                      Select Plant
                    </Button>
                  )}
                  {selectedPlantId === plant.id && (
                    <Chip size="small" label="Active" color="primary" />
                  )}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}

        {plants.length === 0 && (
          <Grid size={{ xs: 12 }}>
            <Paper sx={{ py: 8, textAlign: 'center', px: 4 }}>
              <Typography variant="h6" color="text.secondary" gutterBottom>
                No Solar Plants Configured
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Get started by creating your first solar plant profile.
              </Typography>
              <Button variant="contained" startIcon={<AddCircleIcon />} onClick={handleOpenWizard}>
                Create Plant Profile
              </Button>
            </Paper>
          </Grid>
        )}
      </Grid>

      {/* ─── Multi-step Stepper Dialog (Wizard) ─── */}
      <Dialog open={wizardOpen} onClose={() => setWizardOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ fontWeight: 800 }}>Create Solar Plant Profile</DialogTitle>
        <DialogContent>
          <Box sx={{ py: 3 }}>
            <Stepper activeStep={activeStep} alternativeLabel sx={{ mb: 4 }}>
              {STEPS.map((label) => (
                <Step key={label}>
                  <StepLabel>{label}</StepLabel>
                </Step>
              ))}
            </Stepper>

            <Divider sx={{ mb: 4 }} />

            {/* Step 1: General Info */}
            {activeStep === 0 && (
              <Grid container spacing={3}>
                <Grid size={{ xs: 12, md: 6 }}>
                  <TextField
                    required
                    fullWidth
                    label="Plant Name"
                    name="name"
                    value={formData.name}
                    onChange={handleTextChange}
                    error={formData.name.trim() === ''}
                    helperText={formData.name.trim() === '' ? 'Plant name is required' : ''}
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 6 }}>
                  <TextField
                    required
                    fullWidth
                    label="Location / City"
                    name="location"
                    value={formData.location}
                    onChange={handleTextChange}
                    error={formData.location.trim() === ''}
                    helperText={formData.location.trim() === '' ? 'Location is required' : ''}
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 6 }}>
                  <TextField
                    required
                    fullWidth
                    label="Country"
                    name="country"
                    value={formData.country}
                    onChange={handleTextChange}
                    error={formData.country.trim() === ''}
                    helperText={formData.country.trim() === '' ? 'Country is required' : ''}
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 6 }}>
                  <TextField
                    required
                    fullWidth
                    label="Grid Operator"
                    name="grid_operator"
                    value={formData.grid_operator}
                    onChange={handleTextChange}
                    error={formData.grid_operator.trim() === ''}
                    helperText={formData.grid_operator.trim() === '' ? 'Grid operator is required' : ''}
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 6 }}>
                  <TextField
                    required
                    fullWidth
                    label="Timezone"
                    name="timezone"
                    value={formData.timezone}
                    onChange={handleTextChange}
                    error={formData.timezone.trim() === ''}
                    helperText={formData.timezone.trim() === '' ? 'Timezone is required' : ''}
                  />
                </Grid>
                <Grid size={{ xs: 12 }}>
                  <TextField
                    fullWidth
                    multiline
                    rows={3}
                    label="Notes"
                    name="notes"
                    value={formData.notes || ''}
                    onChange={handleTextChange}
                  />
                </Grid>
              </Grid>
            )}

            {/* Step 2: Specifications */}
            {activeStep === 1 && (
              <Grid container spacing={3}>
                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField
                    required
                    fullWidth
                    type="number"
                    label="Installed DC Capacity (MWp)"
                    value={formData.installed_dc_capacity_mw}
                    onChange={(e) => handleNumberChange('installed_dc_capacity_mw', e.target.value)}
                    error={formData.installed_dc_capacity_mw <= 0}
                    helperText={formData.installed_dc_capacity_mw <= 0 ? 'Must be greater than 0' : ''}
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField
                    required
                    fullWidth
                    type="number"
                    label="Installed AC Capacity (MW)"
                    value={formData.installed_ac_capacity_mw}
                    onChange={(e) => handleNumberChange('installed_ac_capacity_mw', e.target.value)}
                    error={formData.installed_ac_capacity_mw <= 0}
                    helperText={formData.installed_ac_capacity_mw <= 0 ? 'Must be greater than 0' : ''}
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField
                    required
                    fullWidth
                    type="date"
                    label="Commission Date"
                    name="commission_date"
                    value={formData.commission_date}
                    onChange={handleTextChange}
                    slotProps={{ inputLabel: { shrink: true } }}
                    error={formData.commission_date.trim() === ''}
                    helperText={formData.commission_date.trim() === '' ? 'Commission date is required' : ''}
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField
                    required
                    fullWidth
                    type="number"
                    label="Total Panel Area (sqm)"
                    value={formData.total_panel_area_sqm}
                    onChange={(e) => handleNumberChange('total_panel_area_sqm', e.target.value)}
                    error={formData.total_panel_area_sqm <= 0}
                    helperText={formData.total_panel_area_sqm <= 0 ? 'Must be greater than 0' : ''}
                  />
                </Grid>

                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField
                    required
                    fullWidth
                    label="Panel Manufacturer"
                    name="panel_manufacturer"
                    value={formData.panel_manufacturer}
                    onChange={handleTextChange}
                    error={formData.panel_manufacturer.trim() === ''}
                    helperText={formData.panel_manufacturer.trim() === '' ? 'Manufacturer is required' : ''}
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField
                    required
                    fullWidth
                    label="Panel Model"
                    name="panel_model"
                    value={formData.panel_model}
                    onChange={handleTextChange}
                    error={formData.panel_model.trim() === ''}
                    helperText={formData.panel_model.trim() === '' ? 'Model is required' : ''}
                  />
                </Grid>
              </Grid>
            )}

            {/* Step 3: Operation & Expectations */}
            {activeStep === 2 && (
              <Grid container spacing={3}>
                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField
                    required
                    fullWidth
                    type="number"
                    label="Module Efficiency (%)"
                    value={formData.module_efficiency}
                    onChange={(e) => handleNumberChange('module_efficiency', e.target.value)}
                    error={formData.module_efficiency <= 0 || formData.module_efficiency > 100}
                    helperText={(formData.module_efficiency <= 0 || formData.module_efficiency > 100) ? 'Must be between 0 and 100%' : ''}
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField
                    required
                    fullWidth
                    type="number"
                    label="Daily Running Hours"
                    value={formData.daily_running_hours}
                    onChange={(e) => handleNumberChange('daily_running_hours', e.target.value)}
                    error={formData.daily_running_hours <= 0 || formData.daily_running_hours > 24}
                    helperText={(formData.daily_running_hours <= 0 || formData.daily_running_hours > 24) ? 'Must be between 0 and 24' : ''}
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField
                    required
                    fullWidth
                    type="number"
                    label="Annual Degradation Rate (%)"
                    value={formData.annual_degradation_rate}
                    onChange={(e) => handleNumberChange('annual_degradation_rate', e.target.value)}
                    error={formData.annual_degradation_rate < 0 || formData.annual_degradation_rate > 100}
                    helperText={(formData.annual_degradation_rate < 0 || formData.annual_degradation_rate > 100) ? 'Must be between 0 and 100%' : ''}
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField
                    required
                    fullWidth
                    type="number"
                    label="Expected PR (%)"
                    value={formData.expected_pr}
                    onChange={(e) => handleNumberChange('expected_pr', e.target.value)}
                    error={formData.expected_pr <= 0 || formData.expected_pr > 100}
                    helperText={(formData.expected_pr <= 0 || formData.expected_pr > 100) ? 'Must be between 0 and 100%' : ''}
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField
                    required
                    fullWidth
                    type="number"
                    label="Expected CUF (%)"
                    value={formData.expected_cuf}
                    onChange={(e) => handleNumberChange('expected_cuf', e.target.value)}
                    error={formData.expected_cuf <= 0 || formData.expected_cuf > 100}
                    helperText={(formData.expected_cuf <= 0 || formData.expected_cuf > 100) ? 'Must be between 0 and 100%' : ''}
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 4 }}>
                  <TextField
                    required
                    fullWidth
                    type="number"
                    label="Expected Availability (%)"
                    value={formData.expected_availability}
                    onChange={(e) => handleNumberChange('expected_availability', e.target.value)}
                    error={formData.expected_availability <= 0 || formData.expected_availability > 100}
                    helperText={(formData.expected_availability <= 0 || formData.expected_availability > 100) ? 'Must be between 0 and 100%' : ''}
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 6 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={formData.has_weather_station}
                        onChange={(e) => handleSelectChange('has_weather_station', e.target.checked)}
                        color="primary"
                      />
                    }
                    label="Has Integrated Weather Station"
                  />
                </Grid>
                <Grid size={{ xs: 12, md: 6 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={formData.has_string_monitoring}
                        onChange={(e) => handleSelectChange('has_string_monitoring', e.target.checked)}
                        color="primary"
                      />
                    }
                    label="Has String Level Monitoring"
                  />
                </Grid>
              </Grid>
            )}
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3 }}>
          <Button disabled={activeStep === 0} onClick={handleBack}>
            Back
          </Button>
          {activeStep < STEPS.length - 1 ? (
            <Button variant="contained" onClick={handleNext} disabled={isNextDisabled}>
              Next
            </Button>
          ) : (
            <Button variant="contained" color="success" onClick={handleSavePlant} disabled={!isStep3Valid}>
              Register Plant
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* ─── Edit Plant Specifications Dialog ─── */}
      <Dialog open={editOpen} onClose={() => setEditOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ fontWeight: 800 }}>Edit Plant Specifications & Profile</DialogTitle>
        <DialogContent dividers>
          <Box sx={{ py: 1, display: 'flex', flexDirection: 'column', gap: 3 }}>
            <Typography variant="body2" color="text.secondary">
              Update any technical, geographical, or baseline operational parameters for this solar plant.
            </Typography>

            {/* General Info */}
            <Typography variant="subtitle2" sx={{ fontWeight: 700, color: 'primary.main', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              General Information
            </Typography>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth
                  label="Plant Name"
                  value={editFormData.name || ''}
                  onChange={(e) => handleEditFieldChange('name', e.target.value)}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth
                  label="Location / City"
                  value={editFormData.location || ''}
                  onChange={(e) => handleEditFieldChange('location', e.target.value)}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <TextField
                  fullWidth
                  label="Country"
                  value={editFormData.country || ''}
                  onChange={(e) => handleEditFieldChange('country', e.target.value)}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <TextField
                  fullWidth
                  label="Grid Operator"
                  value={editFormData.grid_operator || ''}
                  onChange={(e) => handleEditFieldChange('grid_operator', e.target.value)}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <TextField
                  fullWidth
                  type="date"
                  label="Commission Date"
                  slotProps={{ inputLabel: { shrink: true } }}
                  value={editFormData.commission_date ? String(editFormData.commission_date).split('T')[0] : ''}
                  onChange={(e) => handleEditFieldChange('commission_date', e.target.value)}
                />
              </Grid>
            </Grid>

            <Divider />

            {/* Capacity & Topology */}
            <Typography variant="subtitle2" sx={{ fontWeight: 700, color: 'primary.main', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Capacity & Plant Topology
            </Typography>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 4 }}>
                <TextField
                  fullWidth
                  type="number"
                  label="Installed DC Capacity (MWp)"
                  value={editFormData.installed_dc_capacity_mw ?? ''}
                  onChange={(e) => handleEditFieldChange('installed_dc_capacity_mw', parseFloat(e.target.value) || 0)}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <TextField
                  fullWidth
                  type="number"
                  label="Installed AC Capacity (MW)"
                  value={editFormData.installed_ac_capacity_mw ?? ''}
                  onChange={(e) => handleEditFieldChange('installed_ac_capacity_mw', parseFloat(e.target.value) || 0)}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <TextField
                  fullWidth
                  type="number"
                  label="Total Inverters"
                  value={editFormData.number_of_inverters ?? ''}
                  onChange={(e) => handleEditFieldChange('number_of_inverters', parseInt(e.target.value, 10) || 1)}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <TextField
                  fullWidth
                  label="Panel Manufacturer"
                  value={editFormData.panel_manufacturer || ''}
                  onChange={(e) => handleEditFieldChange('panel_manufacturer', e.target.value)}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <TextField
                  fullWidth
                  label="Panel Model"
                  value={editFormData.panel_model || ''}
                  onChange={(e) => handleEditFieldChange('panel_model', e.target.value)}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <TextField
                  fullWidth
                  type="number"
                  label="Total Panel Area (sqm)"
                  value={editFormData.total_panel_area_sqm ?? ''}
                  onChange={(e) => handleEditFieldChange('total_panel_area_sqm', parseFloat(e.target.value) || 0)}
                />
              </Grid>
            </Grid>

            <Divider />

            {/* Baseline Operational Targets */}
            <Typography variant="subtitle2" sx={{ fontWeight: 700, color: 'primary.main', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Operational Constants & Expected Targets
            </Typography>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 4 }}>
                <TextField
                  fullWidth
                  type="number"
                  label="Module Efficiency (%)"
                  value={editFormData.module_efficiency ?? ''}
                  onChange={(e) => handleEditFieldChange('module_efficiency', parseFloat(e.target.value) || 0)}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <TextField
                  fullWidth
                  type="number"
                  label="Daily Sun Running Hours"
                  value={editFormData.daily_running_hours ?? ''}
                  onChange={(e) => handleEditFieldChange('daily_running_hours', parseFloat(e.target.value) || 0)}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <TextField
                  fullWidth
                  type="number"
                  label="Annual Degradation Rate (%)"
                  value={editFormData.annual_degradation_rate ?? ''}
                  onChange={(e) => handleEditFieldChange('annual_degradation_rate', parseFloat(e.target.value) || 0)}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <TextField
                  fullWidth
                  type="number"
                  label="Expected PR (%)"
                  value={editFormData.expected_pr ?? ''}
                  onChange={(e) => handleEditFieldChange('expected_pr', parseFloat(e.target.value) || 0)}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <TextField
                  fullWidth
                  type="number"
                  label="Expected CUF (%)"
                  value={editFormData.expected_cuf ?? ''}
                  onChange={(e) => handleEditFieldChange('expected_cuf', parseFloat(e.target.value) || 0)}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 4 }}>
                <TextField
                  fullWidth
                  type="number"
                  label="Expected Availability (%)"
                  value={editFormData.expected_availability ?? ''}
                  onChange={(e) => handleEditFieldChange('expected_availability', parseFloat(e.target.value) || 0)}
                />
              </Grid>
            </Grid>

            <Divider />

            {/* Notes */}
            <TextField
              fullWidth
              multiline
              rows={2}
              label="Plant Notes & Technical Remarks"
              value={editFormData.notes || ''}
              onChange={(e) => handleEditFieldChange('notes', e.target.value)}
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={() => setEditOpen(false)}>Cancel</Button>
          <Button variant="contained" color="primary" onClick={handleSavePlantEdit}>
            Save All Changes
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
