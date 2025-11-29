import { BrowserRouter as Router, Routes, Route } from "react-router-dom"
import { ThemeProvider } from "./components/ui/theme-provider"
import { Toaster } from "./components/ui/toaster"
import { Welcome } from "./pages/Welcome"
import { Questionnaire } from "./pages/Questionnaire"
import { Candidates } from "./pages/Candidates"
import { Analysis } from "./pages/Analysis"
import { Results } from "./pages/Results"

function App() {
  return (
    <ThemeProvider defaultTheme="light" storageKey="ui-theme">
      <Router>
        <Routes>
          <Route path="/" element={<Welcome />} />
          <Route path="/questionnaire" element={<Questionnaire />} />
          <Route path="/candidates" element={<Candidates />} />
          <Route path="/analysis" element={<Analysis />} />
          <Route path="/results" element={<Results />} />
        </Routes>
      </Router>
      <Toaster />
    </ThemeProvider>
  )
}

export default App