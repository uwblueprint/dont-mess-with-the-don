import "bootstrap/dist/css/bootstrap.min.css";
import React, { useReducer } from "react";
import { BrowserRouter as Router, Route, Switch } from "react-router-dom";

import CreatePage from "./components/pages/CreatePage";
import Default from "./components/pages/Default";
import DisplayPage from "./components/pages/DisplayPage";
import SimpleEntityCreatePage from "./components/pages/SimpleEntityCreatePage";
import SimpleEntityDisplayPage from "./components/pages/SimpleEntityDisplayPage";
import NotFound from "./components/pages/NotFound";
import UpdatePage from "./components/pages/UpdatePage";
import SimpleEntityUpdatePage from "./components/pages/SimpleEntityUpdatePage";
import * as Routes from "./constants/Routes";
import SampleContext, {
  DEFAULT_SAMPLE_CONTEXT,
} from "./contexts/SampleContext";
import sampleContextReducer from "./reducers/SampleContextReducer";
import SampleContextDispatcherContext from "./contexts/SampleContextDispatcherContext";
import EditTeamInfoPage from "./components/pages/EditTeamPage";
import HooksDemo from "./components/pages/HooksDemo";
import QRCodePOC from "./components/pages/QRCodePOC";
import LoginPage from "./components/pages/LoginPage";
import SignUpPage from "./components/pages/SignUpPage";
import CompleteProfilePage from "./components/pages/CompleteProfilePage";
import AdminHomePage from "./components/pages/AdminHomePage";
import AttendeeHomePage from "./components/pages/AttendeeHomePage";
import PrivateRoute from "./components/auth/PrivateRoute";
import { AuthProvider } from "./contexts/AuthContext";
import MapPOC from "./components/pages/MapPOC";

const App = (): React.ReactElement => {
  // Some sort of global state. Context API replaces redux.
  // Split related states into different contexts as necessary.
  // Split dispatcher and state into separate contexts as necessary.
  const [sampleContext, dispatchSampleContextUpdate] = useReducer(
    sampleContextReducer,
    DEFAULT_SAMPLE_CONTEXT,
  );

  return (
    <AuthProvider>
      <SampleContext.Provider value={sampleContext}>
        <SampleContextDispatcherContext.Provider
          value={dispatchSampleContextUpdate}
        >
          <Router>
            <Switch>
              <Route exact path={Routes.HOME_PAGE} component={Default} />
              <Route
                exact
                path={Routes.CREATE_ENTITY_PAGE}
                component={CreatePage}
              />
              <Route
                exact
                path={Routes.UPDATE_ENTITY_PAGE}
                component={UpdatePage}
              />
              <Route
                exact
                path={Routes.DISPLAY_ENTITY_PAGE}
                component={DisplayPage}
              />
              <Route
                exact
                path={Routes.EDIT_TEAM_PAGE}
                component={EditTeamInfoPage}
              />
              <Route
                exact
                path={Routes.CREATE_SIMPLE_ENTITY_PAGE}
                component={SimpleEntityCreatePage}
              />
              <Route
                exact
                path={Routes.UPDATE_SIMPLE_ENTITY_PAGE}
                component={SimpleEntityUpdatePage}
              />
              <Route
                exact
                path={Routes.DISPLAY_SIMPLE_ENTITY_PAGE}
                component={SimpleEntityDisplayPage}
              />
              <Route exact path={Routes.HOOKS_PAGE} component={HooksDemo} />
              <Route
                exact
                path={Routes.QR_CODE_POC_PAGE}
                component={QRCodePOC}
              />
              <Route exact path={Routes.LOGIN_PAGE} component={LoginPage} />
              <Route exact path={Routes.SIGNUP_PAGE} component={SignUpPage} />
              <Route
                exact
                path={Routes.COMPLETE_PROFILE_PAGE}
                component={CompleteProfilePage}
              />
              <PrivateRoute
                exact
                path={Routes.ADMIN_HOME_PAGE}
                allowedRole="admin"
                component={AdminHomePage}
              />
              <PrivateRoute
                exact
                path={Routes.ATTENDEE_HOME_PAGE}
                allowedRole="attendee"
                component={AttendeeHomePage}
              />
              <Route exact path={Routes.MAP_POC_PAGE} component={MapPOC} />
              <Route exact path="*" component={NotFound} />
            </Switch>
          </Router>
        </SampleContextDispatcherContext.Provider>
      </SampleContext.Provider>
    </AuthProvider>
  );
};

export default App;
