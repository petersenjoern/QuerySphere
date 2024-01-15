import "react-toastify/dist/ReactToastify.css";
import { useState, useRef } from "react";
import { SourceBubble, Source } from "./SourceBubble_Refactor";
import {
  VStack,
  Flex,
  Heading,
  HStack,
  Box,
  Divider,
} from "@chakra-ui/react";
import { InlineCitation } from "./InlineCitation";

export type Message = {
  id: string;
  createdAt?: Date;
  content: string;
  role: "system" | "user" | "assistant" | "function";
  runId?: string;
  sources?: Source[];
  name?: string;
  function_call?: { name: string };
};
export type Feedback = {
  feedback_id: string;
  run_id: string;
  key: string;
  score: number;
  comment?: string;
};

const filterSources = (sources: Source[]) => {
  const filtered: Source[] = [];
  const urlMap = new Map<string, number>();
  const indexMap = new Map<number, number>();
  sources.forEach((source, i) => {
    const { url } = source;
    const index = urlMap.get(url);
    if (index === undefined) {
      urlMap.set(url, i);
      indexMap.set(i, filtered.length);
      filtered.push(source);
    } else {
      const resolvedIndex = indexMap.get(index);
      if (resolvedIndex !== undefined) {
        indexMap.set(i, resolvedIndex);
      }
    }
  });
  return { filtered, indexMap };
};

const createAnswerElements = (
  content: string,
  filteredSources: Source[],
  sourceIndexMap: Map<number, number>,
  highlighedSourceLinkStates: boolean[],
  setHighlightedSourceLinkStates: React.Dispatch<
    React.SetStateAction<boolean[]>
  >,
) => {
  const matches = Array.from(content.matchAll(/\[\^?(\d+)\^?\]/g));
  const elements: JSX.Element[] = [];
  let prevIndex = 0;

  matches.forEach((match) => {
    const sourceNum = parseInt(match[1], 10);
    const resolvedNum = sourceIndexMap.get(sourceNum) ?? 10;
    if (match.index !== null && resolvedNum < filteredSources.length) {
      elements.push(
        <span
          key={`content:${prevIndex}`}
          dangerouslySetInnerHTML={{
            __html: content.slice(prevIndex, match.index),
          }}
        ></span>,
      );
      elements.push(
        <InlineCitation
          key={`citation:${prevIndex}`}
          source={filteredSources[resolvedNum]}
          sourceNumber={resolvedNum}
          highlighted={highlighedSourceLinkStates[resolvedNum]}
          onMouseEnter={() =>
            setHighlightedSourceLinkStates(
              filteredSources.map((_, i) => i === resolvedNum),
            )
          }
          onMouseLeave={() =>
            setHighlightedSourceLinkStates(filteredSources.map(() => false))
          }
        />,
      );
      prevIndex = (match?.index ?? 0) + match[0].length;
    }
  });
  elements.push(
    <span
      key={`content:${prevIndex}`}
      dangerouslySetInnerHTML={{ __html: content.slice(prevIndex) }}
    ></span>,
  );
  return elements;
};

export function ChatMessageBubble(props: {
  message: Message;
  isMostRecent: boolean;
  messageCompleted: boolean;
}) {
  const { role, content } = props.message;
  const isUser = role === "user";
  // const [isLoading, setIsLoading] = useState(false);
  // const [traceIsLoading, setTraceIsLoading] = useState(false);
  // const [feedback, setFeedback] = useState<Feedback | null>(null);
  // const [comment, setComment] = useState("");
  // const [feedbackColor, setFeedbackColor] = useState("");
  // const upButtonRef = useRef(null);
  // const downButtonRef = useRef(null);

  const sources = props.message.sources ?? [];
  const { filtered: filteredSources, indexMap: sourceIndexMap } =
    filterSources(sources);

  // Use an array of highlighted states as a state since React
  // complains when creating states in a loop
  const [highlighedSourceLinkStates, setHighlightedSourceLinkStates] = useState(
    filteredSources.map(() => false),
  );
  const answerElements =
    role === "assistant"
      ? createAnswerElements(
          content,
          filteredSources,
          sourceIndexMap,
          highlighedSourceLinkStates,
          setHighlightedSourceLinkStates,
        )
      : [];

  return (
    <VStack align="start" spacing={5} pb={5}>
      {!isUser && filteredSources.length > 0 && (
        <>
          <Flex direction={"column"} width={"100%"}>
            <VStack spacing={"5px"} align={"start"} width={"100%"}>
              <Heading
                fontSize="lg"
                fontWeight={"medium"}
                mb={1}
                color={"rgb(252, 163, 17)"}
                paddingBottom={"10px"}
              >
                Sources
              </Heading>
              <HStack spacing={"10px"} maxWidth={"100%"} overflow={"auto"}>
                {filteredSources.map((source, index) => (
                  <Box key={index} alignSelf={"stretch"} width={40}>
                    <SourceBubble
                      source={source}
                      highlighted={highlighedSourceLinkStates[index]}
                      onMouseEnter={() =>
                        setHighlightedSourceLinkStates(
                          filteredSources.map((_, i) => i === index),
                        )
                      }
                      onMouseLeave={() =>
                        setHighlightedSourceLinkStates(
                          filteredSources.map(() => false),
                        )
                      }
                    />
                  </Box>
                ))}
              </HStack>
            </VStack>
          </Flex>

          <Heading size="lg" fontWeight="medium" color="rgb(252, 163, 17)">
            Answer
          </Heading>
        </>
      )}

      {isUser ? (
        <Heading size="lg" fontWeight="medium" color="rgb(20, 33, 61)">
          {content}
        </Heading>
      ) : (
        <Box className="whitespace-pre-wrap" color="rgb(20, 33, 61)">
          {answerElements}
        </Box>
      )}

      {!isUser && <Divider mt={4} mb={4} />}
    </VStack>
  );
}