import { Route, Routes } from 'react-router-dom'
import Choose from './screens/Choose'
import Home from './screens/Home'
import MicCheck from './screens/MicCheck'
import Result from './screens/Result'
import Room from './screens/Room'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/choose" element={<Choose />} />
      <Route path="/mic" element={<MicCheck />} />
      <Route path="/room/:id" element={<Room />} />
      <Route path="/result/:id" element={<Result />} />
    </Routes>
  )
}
