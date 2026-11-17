import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  GoogleAuthProvider,
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
} from "firebase/auth";

import AuthAPIClient from "../APIClients/AuthAPIClient";
import auth from "../firebase";
import {
  AuthStatus,
  AuthenticatedUser,
  RegisterRequest,
} from "../types/AuthTypes";

type AuthContextValue = {
  status: AuthStatus;
  // Our profile from GET /users/me; null until status is "signedIn"
  user: AuthenticatedUser | null;
  logIn: (email: string, password: string) => Promise<void>;
  logInWithGoogle: () => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  completeProfile: (profile: RegisterRequest) => Promise<void>;
  logOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export const AuthProvider = ({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement => {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthenticatedUser | null>(null);

  // Firebase keeps the session across reloads; on every sign-in or sign-out
  // load our profile for that account
  useEffect(
    () =>
      onAuthStateChanged(auth, async (firebaseUser) => {
        if (!firebaseUser) {
          setUser(null);
          setStatus("signedOut");
          return;
        }
        setStatus("loading");
        try {
          const me = await AuthAPIClient.getMe();
          setUser(me);
          setStatus(me ? "signedIn" : "needsProfile");
        } catch {
          // Backend unreachable or token rejected: don't leave a half signed-in state
          await signOut(auth);
        }
      }),
    [],
  );

  const logIn = useCallback(async (email: string, password: string) => {
    await signInWithEmailAndPassword(auth, email, password);
  }, []);

  const logInWithGoogle = useCallback(async () => {
    await signInWithPopup(auth, new GoogleAuthProvider());
  }, []);

  const signUp = useCallback(async (email: string, password: string) => {
    await createUserWithEmailAndPassword(auth, email, password);
  }, []);

  const completeProfile = useCallback(async (profile: RegisterRequest) => {
    const me = await AuthAPIClient.register(profile);
    setUser(me);
    setStatus("signedIn");
  }, []);

  const logOut = useCallback(async () => {
    await signOut(auth);
  }, []);

  const value = useMemo(
    () => ({
      status,
      user,
      logIn,
      logInWithGoogle,
      signUp,
      completeProfile,
      logOut,
    }),
    [status, user, logIn, logInWithGoogle, signUp, completeProfile, logOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextValue => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside an AuthProvider");
  }
  return context;
};
