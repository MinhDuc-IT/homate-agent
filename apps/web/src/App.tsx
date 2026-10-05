import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { RequireAdmin } from '@/components/auth/RequireAdmin'
import { RequireAuth } from '@/components/auth/RequireAuth'
import { AppLayout } from '@/components/layout/AppLayout'
import { Providers } from '@/components/providers/Providers'
import { ROUTES } from '@/config/routes'
import { AI_ENABLED } from '@/config/features'
import { AiPending } from '@/screens/AiPending'
import { CameraScreen } from '@/screens/CameraScreen'
import { ClarifyDialog } from '@/screens/ClarifyDialog'
import { Dashboard } from '@/screens/Dashboard'
import { DeviceScreen } from '@/screens/DeviceScreen'
import { EnergyScreen } from '@/screens/EnergyScreen'
import { HitlDialog } from '@/screens/HitlDialog'
import { Login } from '@/screens/Login'
import { RoomScreen } from '@/screens/RoomScreen'
import { SceneManager } from '@/screens/SceneManager'
import { SceneScreen } from '@/screens/SceneScreen'
import { ScheduleScreen } from '@/screens/ScheduleScreen'
import { SettingScreen } from '@/screens/SettingScreen'
import { UiKit } from '@/screens/UiKit'
import { VoiceAgentPage } from '@/screens/VoiceAgentPage'
import { VoicePanel } from '@/screens/VoicePanel'

export default function App() {
  return (
    <Providers>
      <BrowserRouter>
        <Routes>
          <Route path={ROUTES.login} element={<Login />} />
          <Route path="/" element={<Navigate to={ROUTES.dashboard} replace />} />

          <Route element={<RequireAuth />}>
            <Route path={ROUTES.voiceAgent} element={AI_ENABLED ? <VoiceAgentPage /> : <AiPending />} />

            <Route element={<AppLayout />}>
              <Route path={ROUTES.dashboard} element={<Dashboard />} />
              <Route path={ROUTES.room} element={<RoomScreen />} />
              <Route path={ROUTES.energy} element={<EnergyScreen />} />
              <Route path={ROUTES.devices} element={<DeviceScreen />} />
              <Route path={ROUTES.camera} element={<CameraScreen />} />
              <Route path={ROUTES.scenes} element={<SceneScreen />} />
              <Route path={ROUTES.schedules} element={<ScheduleScreen />} />
              <Route path={ROUTES.settings} element={<SettingScreen />} />
              <Route path={ROUTES.voice} element={AI_ENABLED ? <VoicePanel /> : <AiPending />} />
              <Route path={ROUTES.clarify} element={AI_ENABLED ? <ClarifyDialog /> : <AiPending />} />
              <Route path={ROUTES.hitl} element={AI_ENABLED ? <HitlDialog /> : <AiPending />} />

              <Route
                path={ROUTES.scenarios}
                element={
                  <RequireAdmin>
                    <SceneManager />
                  </RequireAdmin>
                }
              />

              <Route
                path={ROUTES.mock}
                element={
                  <RequireAdmin>
                    <Navigate to={`${ROUTES.settings}?tab=mock`} replace />
                  </RequireAdmin>
                }
              />

              <Route path={ROUTES.uiKit} element={<UiKit />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to={ROUTES.dashboard} replace />} />
        </Routes>
      </BrowserRouter>
    </Providers>
  )
}
