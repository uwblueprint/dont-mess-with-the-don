import { MapEvent } from "./sampleEvents";

// Every provider map implements these props so they are interchangeable.
export type EventMapProps = {
  events: MapEvent[];
  selectedEventId: string | null;
  onSelectEvent: (eventId: string | null) => void;
};
