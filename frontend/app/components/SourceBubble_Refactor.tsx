import "react-toastify/dist/ReactToastify.css";
import { Card, CardBody, Heading } from "@chakra-ui/react";

export type Source = {
  url: string;
  title: string;    
};

export function SourceBubble({
  source,
  highlighted,
  onMouseEnter,
  onMouseLeave,
}: {
  source: Source;
  highlighted: boolean;
  onMouseEnter: () => any;
  onMouseLeave: () => any;
}) {
  return (
    <Card
      onClick={async () => {
        window.open(source.url, "_blank");
      }}
      backgroundColor={highlighted ? "rgb(255, 255, 255)" : "rgb(229, 229, 229)"}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      cursor={"pointer"}
      alignSelf={"stretch"}
      height="100%"
      overflow={"hidden"}
    >
      <CardBody>
        <Heading size={"sm"} fontWeight={"normal"} color={"rgb(20, 33, 61)"}>
          {source.title}
        </Heading>
      </CardBody>
    </Card>
  );
}