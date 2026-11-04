import React from 'react';
import { Box, Card, CardContent, Typography, Chip } from '@mui/material';
import ConstructionRoundedIcon from '@mui/icons-material/ConstructionRounded';
import { ACCENT_GRADIENT } from '../theme/theme';

interface PlaceholderPageProps {
  title: string;
  description?: string;
}

const PlaceholderPage: React.FC<PlaceholderPageProps> = ({
  title,
  description = 'This module will be implemented in a future task.',
}) => {
  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 'calc(100vh - 200px)',
        p: 4,
      }}
    >
      <Card
        sx={{
          maxWidth: 480,
          width: '100%',
          textAlign: 'center',
          py: 6,
          px: 4,
          position: 'relative',
          overflow: 'visible',
        }}
      >
        {/* Gradient top accent */}
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: '50%',
            transform: 'translateX(-50%) translateY(-50%)',
            width: 72,
            height: 72,
            borderRadius: '20px',
            background: ACCENT_GRADIENT,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 8px 32px rgba(0,191,166,0.3)',
          }}
        >
          <ConstructionRoundedIcon sx={{ fontSize: 36, color: '#fff' }} />
        </Box>

        <CardContent sx={{ pt: 5 }}>
          <Chip
            label="Coming Soon"
            size="small"
            sx={{
              mb: 2,
              fontWeight: 600,
              background: 'rgba(0,191,166,0.12)',
              color: 'primary.main',
              border: '1px solid rgba(0,191,166,0.2)',
            }}
          />
          <Typography variant="h4" gutterBottom sx={{ fontWeight: 700 }}>
            {title}
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ lineHeight: 1.7 }}>
            {description}
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
};

export default PlaceholderPage;
