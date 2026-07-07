import React from "react";
import QRCode from "react-qr-code";

import MainPageButton from "../common/MainPageButton";

const QR_URL = "https://youtu.be/dQw4w9WgXcQ?si=upi77EeghU3vGmCs";

const QRCodePOC = (): React.ReactElement => {
  return (
    <div className="text-center py-4">
      <MainPageButton />
      <h1 className="mb-2 mt-3">QR Code POC</h1>

      <div className="d-inline-block p-3 shadow-lg bg-primary">
        <div
          className="bg-white p-3"
          style={{
            boxShadow: "inset 0 0 0 1px rgba(255, 255, 255, 0.04)",
          }}
        >
          <QRCode
            value={QR_URL}
            size={256}
            fgColor="#1e293b"
            bgColor="white"
            level="L"
            style={{
              height: "auto",
              maxWidth: "100%",
              width: "100%",
              display: "block",
            }}
          />
        </div>
      </div>
    </div>
  );
};

export default QRCodePOC;