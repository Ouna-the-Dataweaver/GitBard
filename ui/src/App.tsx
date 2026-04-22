import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Original from "./versions/Original";
import V1CleanModern from "./versions/V1CleanModern";
import V2GlassNeon from "./versions/V2GlassNeon";
import V3LightTabs from "./versions/V3LightTabs";
import V4GraphCentric from "./versions/V4GraphCentric";

function App() {
  return (
    <BrowserRouter basename="/admin">
      <Routes>
        <Route path="/" element={<Navigate to="/v4" replace />} />
        <Route path="/v0" element={<Original />} />
        <Route path="/v1" element={<V1CleanModern />} />
        <Route path="/v2" element={<V2GlassNeon />} />
        <Route path="/v3" element={<V3LightTabs />} />
        <Route path="/v4" element={<V4GraphCentric />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
