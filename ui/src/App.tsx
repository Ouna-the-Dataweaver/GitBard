import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Onboarding from "./versions/Onboarding";
import V4GraphCentric from "./versions/V4GraphCentric";

function App() {
  return (
    <BrowserRouter basename="/admin">
      <Routes>
        <Route path="/" element={<Navigate to="/v4" replace />} />
        <Route path="/v4" element={<V4GraphCentric />} />
        <Route path="/onboarding" element={<Onboarding />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
