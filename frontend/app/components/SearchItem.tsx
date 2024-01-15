import React, { MouseEventHandler } from 'react';
import { Box, List, Text, useColorModeValue } from '@chakra-ui/react';
interface SearchItemProps {
  source: string;
  title: string;
  isSelected: boolean;
  onClick: MouseEventHandler<HTMLDivElement>;
}

const SearchItem: React.FC<SearchItemProps> = ({ source, title, isSelected, onClick }) => {
    // Set text color based on the current color mode (light or dark)
    const textColor = useColorModeValue('rgb(254, 197, 187)', 'rgb(254, 197, 187)');
  
    return (
      <Box
        justifyContent="center"
        color={textColor}
        bg={isSelected ? "rgb(216, 226, 220)" : 'transparent'}
        borderRadius="md"
        cursor="pointer"
        px={3}
        py={2}
        transition="all 0.2s ease-in-out"
        _hover={{ bg: 'rgb(216, 226, 220)', transition: 'all 0.2s ease-in-out' }}
        onClick={onClick}
      >
        <Text fontSize="sm" className="truncate" title={`${title} | ${source}`}>{`${title} | ${source}`}</Text>
      </Box>
    );
  };
  
  export default SearchItem;
  
