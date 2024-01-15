import React, { useState, useCallback } from 'react';
import { Input, InputGroup, InputLeftElement, Flex, Center, Box } from '@chakra-ui/react';
import { SearchIcon } from '@chakra-ui/icons';
import SearchItem from './SearchItem';
import SourceTitlePair from './MyTable.tsx'

interface SearchBarProps {
    items: SourceTitlePair[];
    onFilter: (selectedSources: string[]) => void;
  }



const SearchBar: React.FC<SearchBarProps> = ({ items, onFilter }) => {
  const [searchValue, setSearchValue] = useState('');
  const [selectedItems, setSelectedItems] = useState<string[]>([]);

  const handleInputChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value;
    setSearchValue(value);

    if (!value) {
      onFilter([]);
      return;
    }

    // Filter matching items based on the search input
    const matchingItems = items.filter((item) => item.title.toLowerCase().includes(value.toLowerCase()));

    // Convert selected indexes to corresponding sources
    const selectedSources = new Set(selectedItems);
    const currentIndexedSources = matchingItems.map((item, index) => (selectedItems.includes(index.toString()) ? item.source : null)).filter(Boolean);
    const selectedMatchingSources = Array.from(new Set([...currentIndexedSources, ...Array.from(selectedSources)]));

    onFilter(selectedMatchingSources);
  }, [items, selectedItems, onFilter]);


  const toggleItemSelection = (id: string) => {
    if (selectedItems.includes(id)) {
      setSelectedItems(selectedItems.filter((itemId) => itemId !== id));
    } else {
      setSelectedItems([...selectedItems, id]);
    }
  };

  return (
    <Box 
        backgroundColor={"rgb(255, 229, 217)"}
        cursor={"pointer"}
        justifyContent={"center"}
    >
      <InputGroup>
        <InputLeftElement pointerEvents={"none"}>
          <SearchIcon color={"rgb(254, 197, 187)"} />
        </InputLeftElement>
        <Input type="text" placeholder="Search..." color={"rgb(254, 197, 187)"} value={searchValue} onChange={handleInputChange} />
      </InputGroup>
      {items
        .filter((item) => item.title.toLowerCase().includes(searchValue.toLowerCase()))
        .map((item) => (
          <SearchItem
            key={item.id}
            source={item.source}
            title={item.title}
            isSelected={selectedItems.includes(item.source)}
            onClick={() => toggleItemSelection(item.source)}
          />
        ))}
    </Box>
  );
};
export default SearchBar;
