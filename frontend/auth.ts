import NextAuth from "next-auth";
import GitHub from "next-auth/providers/github";

// Frontend (reposage-two.vercel.app) and backend (reposage-a0n6.onrender.com) are on
// different domains, so the session cookie must be sent cross-site. Browsers only send
// cross-site cookies when SameSite=None and Secure, so we override the default
// SameSite=Lax cookie in production. Left untouched in dev, where NODE_ENV !== "production"
// and the default (unprefixed, SameSite=Lax) cookie continues to work on http://localhost.
const useSecureCookies = process.env.NODE_ENV === "production";

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    GitHub({
      clientId: process.env.AUTH_GITHUB_ID,
      clientSecret: process.env.AUTH_GITHUB_SECRET,
    }),
  ],
  ...(useSecureCookies && {
    cookies: {
      sessionToken: {
        name: "__Secure-authjs.session-token",
        options: {
          httpOnly: true,
          sameSite: "none" as const,
          path: "/",
          secure: true,
        },
      },
    },
  }),
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account && profile) {
        token.sub = String(profile.id);
      }
      return token;
    },
  },
});
