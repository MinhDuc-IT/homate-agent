import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useSession } from "@/context/SessionContext";
import { ROUTES } from "@/config/routes";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

export function RequireAuth() {
  const { session, authReady } = useSession();
  const location = useLocation();

  if (!authReady) {
    return (
      <div className="flex min-h-full items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  if (!session) {
    return (
      <Navigate to={ROUTES.login} replace state={{ from: location.pathname }} />
    );
  }

  return <Outlet />;
}
