import {
  AdvancedMarker,
  APIProvider,
  InfoWindow,
  Map,
  useAdvancedMarkerRef,
  useMap,
} from "@vis.gl/react-google-maps";
import React, { useEffect } from "react";

import EventPopupContent from "./EventPopupContent";
import { MapEvent } from "./sampleEvents";
import { EventMapProps } from "./types";

// Without a key, Google still renders the map in a watermarked
// "for development purposes only" mode, which is enough for this POC.
const API_KEY = process.env.REACT_APP_GOOGLE_MAPS_API_KEY ?? "";
// Advanced markers require a map ID; DEMO_MAP_ID is Google's shared one.
const MAP_ID = process.env.REACT_APP_GOOGLE_MAPS_MAP_ID || "DEMO_MAP_ID";

const SELECTED_ZOOM = 14;

const EventMarker = ({
  event,
  isSelected,
  onSelectEvent,
}: {
  event: MapEvent;
  isSelected: boolean;
  onSelectEvent: EventMapProps["onSelectEvent"];
}): React.ReactElement => {
  const [markerRef, marker] = useAdvancedMarkerRef();

  return (
    <>
      <AdvancedMarker
        ref={markerRef}
        position={{ lat: event.lat, lng: event.lng }}
        title={event.name}
        onClick={() => onSelectEvent(event.id)}
      />
      {isSelected && (
        <InfoWindow anchor={marker} onCloseClick={() => onSelectEvent(null)}>
          <EventPopupContent event={event} />
        </InfoWindow>
      )}
    </>
  );
};

// Pans to the selected event. Lives inside Map because useMap() only works
// there.
const SelectedEventSync = ({
  events,
  selectedEventId,
}: Pick<EventMapProps, "events" | "selectedEventId">): null => {
  const map = useMap();

  useEffect(() => {
    const event = events.find((e) => e.id === selectedEventId);
    if (!map || !event) return;
    map.panTo({ lat: event.lat, lng: event.lng });
    map.setZoom(Math.max(map.getZoom() ?? 0, SELECTED_ZOOM));
  }, [events, selectedEventId, map]);

  return null;
};

const GoogleEventMap = ({
  events,
  selectedEventId,
  onSelectEvent,
}: EventMapProps): React.ReactElement => {
  const lats = events.map((e) => e.lat);
  const lngs = events.map((e) => e.lng);
  const bounds = {
    north: Math.max(...lats),
    south: Math.min(...lats),
    east: Math.max(...lngs),
    west: Math.min(...lngs),
    padding: 40,
  };

  return (
    <div className="d-flex flex-column h-100">
      {!API_KEY && (
        <div className="alert alert-warning small py-2 mb-2">
          No <code>REACT_APP_GOOGLE_MAPS_API_KEY</code> set, so Google renders
          in watermarked development mode. Add a key from the Google Cloud
          Console (Maps JavaScript API) to <code>frontend/.env</code> to remove
          it.
        </div>
      )}
      <div className="flex-grow-1">
        <APIProvider apiKey={API_KEY}>
          <Map
            mapId={MAP_ID}
            defaultBounds={bounds}
            gestureHandling="greedy"
            style={{ height: "100%", width: "100%" }}
          >
            {events.map((event) => (
              <EventMarker
                key={event.id}
                event={event}
                isSelected={event.id === selectedEventId}
                onSelectEvent={onSelectEvent}
              />
            ))}
            <SelectedEventSync
              events={events}
              selectedEventId={selectedEventId}
            />
          </Map>
        </APIProvider>
      </div>
    </div>
  );
};

export default GoogleEventMap;
