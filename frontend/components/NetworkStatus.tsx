"use client";

import { useEffect, useState } from "react";

export default function NetworkStatus() {
    const [offline, setOffline] = useState(false);

    useEffect(() => {
        const updateStatus = () => {
            setOffline(!navigator.onLine);
        };

        updateStatus();

        window.addEventListener("online", updateStatus);
        window.addEventListener("offline", updateStatus);

        return () => {
            window.removeEventListener("online", updateStatus);
            window.removeEventListener("offline", updateStatus);
        };
    }, []);

    if (!offline) return null;

    return (
        <div className="network-warning" role="status">
            You appear to be offline. Keep this page open. Unsaved examination
            answers may not reach NiCat until your connection is restored.
        </div>
    );
}
