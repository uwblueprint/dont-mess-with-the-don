import React from "react";

import { MapEvent } from "./sampleEvents";

const dateFormatter = new Intl.DateTimeFormat("en-CA", {
  weekday: "short",
  month: "short",
  day: "numeric",
  year: "numeric",
});

const timeFormatter = new Intl.DateTimeFormat("en-CA", {
  hour: "numeric",
  minute: "2-digit",
});

export const formatEventTime = (event: MapEvent): string => {
  const start = new Date(event.startDatetime);
  const end = new Date(event.endDatetime);
  return `${dateFormatter.format(start)}, ${timeFormatter.format(
    start,
  )} - ${timeFormatter.format(end)}`;
};

// Google's directions URL works without an API key, whichever map renders it.
const directionsUrl = (event: MapEvent): string =>
  `https://www.google.com/maps/dir/?api=1&destination=${event.lat},${event.lng}`;

const EventPopupContent = ({
  event,
}: {
  event: MapEvent;
}): React.ReactElement => (
  <div style={{ minWidth: 200 }}>
    <h6 className="mb-1">{event.name}</h6>
    <div className="small text-muted mb-1">{event.location}</div>
    <div className="small mb-2">{formatEventTime(event)}</div>
    <span
      className={`badge mr-2 ${
        event.eventStatus === "published" ? "badge-success" : "badge-secondary"
      }`}
    >
      {event.eventStatus}
    </span>
    <a
      className="small"
      href={directionsUrl(event)}
      target="_blank"
      rel="noopener noreferrer"
    >
      Get directions
    </a>
  </div>
);

export default EventPopupContent;
