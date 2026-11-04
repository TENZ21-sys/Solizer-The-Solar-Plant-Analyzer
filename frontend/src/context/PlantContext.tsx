import React, { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { getPlants } from '../services/api';
import type { PlantListItem } from '../types';

interface PlantContextValue {
  plants: PlantListItem[];
  selectedPlantId: number | null;
  setSelectedPlantId: (id: number | null) => void;
  loading: boolean;
  refreshPlants: () => Promise<void>;
  startDate: string | undefined;
  endDate: string | undefined;
  setDateRange: (startDate: string | undefined, endDate: string | undefined) => void;
}

const PlantContext = createContext<PlantContextValue>({
  plants: [],
  selectedPlantId: null,
  setSelectedPlantId: () => {},
  loading: true,
  refreshPlants: async () => {},
  startDate: undefined,
  endDate: undefined,
  setDateRange: () => {},
});

export const usePlant = () => useContext(PlantContext);

interface PlantContextProviderProps {
  children: ReactNode;
}

export const PlantContextProvider: React.FC<PlantContextProviderProps> = ({ children }) => {
  const [plants, setPlants] = useState<PlantListItem[]>([]);
  const [selectedPlantId, setSelectedPlantIdState] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  
  const [startDate, setStartDateState] = useState<string | undefined>(() => {
    return localStorage.getItem('solizer-start-date') || undefined;
  });
  const [endDate, setEndDateState] = useState<string | undefined>(() => {
    return localStorage.getItem('solizer-end-date') || undefined;
  });

  const setDateRange = (start: string | undefined, end: string | undefined) => {
    setStartDateState(start);
    setEndDateState(end);
    if (start) {
      localStorage.setItem('solizer-start-date', start);
    } else {
      localStorage.removeItem('solizer-start-date');
    }
    if (end) {
      localStorage.setItem('solizer-end-date', end);
    } else {
      localStorage.removeItem('solizer-end-date');
    }
  };

  const fetchPlants = async () => {
    try {
      setLoading(true);
      const data = await getPlants();
      setPlants(data);
      
      // If there are plants and none is selected, select the first one
      if (data.length > 0) {
        const savedId = localStorage.getItem('solizer-selected-plant-id');
        const parsedSavedId = savedId ? parseInt(savedId, 10) : null;
        
        // Verify saved ID exists in fetched list
        if (parsedSavedId && data.some(p => p.id === parsedSavedId)) {
          setSelectedPlantIdState(parsedSavedId);
        } else {
          setSelectedPlantIdState(data[0].id);
          localStorage.setItem('solizer-selected-plant-id', data[0].id.toString());
        }
      } else {
        setSelectedPlantIdState(null);
      }
    } catch (err) {
      console.error('Error fetching plants:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlants();
  }, []);

  const setSelectedPlantId = (id: number | null) => {
    setSelectedPlantIdState(id);
    if (id !== null) {
      localStorage.setItem('solizer-selected-plant-id', id.toString());
    } else {
      localStorage.removeItem('solizer-selected-plant-id');
    }
  };

  return (
    <PlantContext.Provider
      value={{
        plants,
        selectedPlantId,
        setSelectedPlantId,
        loading,
        refreshPlants: fetchPlants,
        startDate,
        endDate,
        setDateRange,
      }}
    >
      {children}
    </PlantContext.Provider>
  );
};
