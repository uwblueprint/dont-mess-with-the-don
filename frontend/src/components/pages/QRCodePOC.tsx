import React from "react";
import QRCode from "react-qr-code";
import { QRCodeCanvas, QRCodeSVG } from "qrcode.react";

import MainPageButton from "../common/MainPageButton";

const QR_URL = "https://youtu.be/dQw4w9WgXcQ?si=upi77EeghU3vGmCs";
const BASE_URL = "https://dontmesswiththedon/check-in/";

const QRCodePOC = (): React.ReactElement => {
  return (
    <div className="text-center py-4">
      <MainPageButton />
      <h1 className="mb-2 mt-3">QR Code POC</h1>

      <div className="d-flex flex-wrap justify-content-center align-items-start">
        {/* Not recommended: react-qr-code */}
        <div className="mx-3 mb-3">
          <div
            className="d-inline-block p-3 shadow-lg"
            style={{ backgroundColor: "rgb(227, 29, 36)" }}
          >
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
          <p className="mt-2 mb-0">react-qr-code</p>
        </div>

        {/* Recommended: qrcode.react SVG — more flexible than Canvas */}
        <div className="mx-3 mb-3">
          <div
            className="d-inline-block p-3 shadow-lg"
            style={{ backgroundColor: "rgb(227, 29, 36)" }}
          >
            <div
              className="bg-white p-3"
              style={{
                boxShadow: "inset 0 0 0 1px rgba(255, 255, 255, 0.04)",
              }}
            >
              {/* Recommended: qrcode.react SVG */}
              <QRCodeSVG
                value={`${BASE_URL}event_id={event_id}`}
                size={256}
                level="H"
                bgColor="white"
                fgColor="#1e293b"
                imageSettings={{
                  src: "/dmwtd-logo512.png",
                  height: 96,
                  width: 96,
                  excavate: true,
                }}
              />
            </div>
          </div>
          <p className="mt-2 mb-0">qrcode.react (SVG)</p>
        </div>

        {/* Canvas alternative; SVG is recommended by qrcode.react */}
        <div className="mx-3 mb-3">
          <div
            className="d-inline-block p-3 shadow-lg"
            style={{ backgroundColor: "rgb(227, 29, 36)" }}
          >
            <div
              className="bg-white p-3"
              style={{
                boxShadow: "inset 0 0 0 1px rgba(255, 255, 255, 0.04)",
              }}
            >
              <QRCodeCanvas
                value={`${BASE_URL}event_id={event_id}`}
                size={256}
                level="H"
                bgColor="white"
                fgColor="#1e293b"
                imageSettings={{
                  src: "/dmwtd-logo512.png",
                  height: 96,
                  width: 96,
                  excavate: true,
                }}
              />
            </div>
          </div>
          <p className="mt-2 mb-0">qrcode.react (Canvas)</p>
        </div>
      </div>
    </div>
  );
};

export default QRCodePOC;
