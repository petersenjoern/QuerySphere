import React, { useState } from 'react';
import { Card } from '@chakra-ui/react';
import SearchBar from './SearchBar';

interface SourceTitlePair {
    id: string;
    source: string;
    title: string;
  }

const MyTable: React.FC = () => {
  const [filterValue, setFilterValue] = useState<string>('')
  const data: SourceTitlePair[] = [
    { id: "1", source: "TechTrend Insights", title: "Revolutionizing Quantum Computing with Qubit Sharding" },
    { id: "2", source: "SpaceWonders Magazine", title: "Galactic Marvels: Unraveling the Secrets of Dark Matter Nebulae" },
    { id: "3", source: "EcoVisionary Journal", title: "Sustainable Innovations: Bio-inspired Solutions for Future Agriculture" },
  ];

  return (
    <Card>
      <SearchBar items={data} onFilter={setFilterValue} />
    </Card>
  );
};

export default MyTable;
