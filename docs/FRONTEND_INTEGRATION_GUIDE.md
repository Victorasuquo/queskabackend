# Queska Frontend Integration Guide

## Base URL
```
Production: https://api.queska.com
Development: http://localhost:8000
```

**API Version Prefix**: `/api/v1`

---

## Table of Contents
1. [Authentication](#1-authentication)
2. [Google OAuth Integration](#2-google-oauth-integration)
3. [Dashboard APIs](#3-dashboard-apis)
4. [User Profile Management](#4-user-profile-management)
5. [Token Management](#5-token-management)
6. [Error Handling](#6-error-handling)
7. [TypeScript Interfaces](#7-typescript-interfaces)

---

## 1. Authentication

### 1.1 Email/Password Registration

**Endpoint**: `POST /api/v1/users/register`

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123",
  "first_name": "Victor",
  "last_name": "Asuquo",
  "phone": "+2348012345678"
}
```

**Response** (201 Created):
```json
{
  "success": true,
  "message": "Account created successfully. Please verify your email.",
  "user_id": "507f1f77bcf86cd799439011",
  "email": "user@example.com",
  "referral_code": "QUAB12CD"
}
```

**Password Requirements**:
- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 digit

---

### 1.2 Email/Password Login

**Endpoint**: `POST /api/v1/users/login`

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "507f1f77bcf86cd799439011",
    "email": "user@example.com",
    "first_name": "Victor",
    "last_name": "Asuquo",
    "full_name": "Victor Asuquo",
    "display_name": null,
    "phone": "+2348012345678",
    "bio": null,
    "profile_photo": null,
    "cover_photo": null,
    "status": "active",
    "is_email_verified": true,
    "is_phone_verified": false,
    "is_active": true,
    "followers_count": 0,
    "following_count": 0,
    "experiences_count": 0,
    "reviews_count": 0,
    "referral_code": "QUAB12CD",
    "created_at": "2025-12-17T10:30:00Z",
    "last_login_at": "2025-12-17T14:20:00Z"
  }
}
```

---

## 2. Google OAuth Integration

### 2.1 Check OAuth Status

**Endpoint**: `GET /api/v1/auth/oauth/status`

**Response**:
```json
{
  "google": {
    "enabled": true,
    "login_url": "/api/v1/auth/google/login"
  },
  "facebook": {
    "enabled": false,
    "login_url": null
  },
  "apple": {
    "enabled": false,
    "login_url": null
  }
}
```

---

### 2.2 Option A: Server-Side OAuth Flow (Recommended for Web)

#### Step 1: Get Google Auth URL

**Endpoint**: `GET /api/v1/auth/google/login`

**Query Parameters** (optional):
- `redirect_uri`: Custom URL to redirect after authentication

**Response**:
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=xxx&redirect_uri=https://queska.com/auth/google/callback&response_type=code&scope=openid+email+profile&access_type=offline&prompt=consent"
}
```

#### Step 2: Redirect User to Google
```javascript
// React/Next.js Example
const handleGoogleLogin = async () => {
  const response = await fetch(`${BASE_URL}/api/v1/auth/google/login`);
  const data = await response.json();
  
  // Redirect user to Google
  window.location.href = data.auth_url;
};
```

#### Step 3: Handle Callback
After Google authentication, user is redirected to:
```
https://queska.com/auth/google/callback?code=AUTHORIZATION_CODE
```

Your frontend should:
1. Extract the `code` parameter from the URL
2. Send it to the backend

**Endpoint**: `GET /api/v1/auth/google/callback?code=AUTHORIZATION_CODE`

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "507f1f77bcf86cd799439011",
    "email": "victor@gmail.com",
    "first_name": "Victor",
    "last_name": "Asuquo",
    "full_name": "Victor Asuquo",
    "profile_photo": "https://lh3.googleusercontent.com/a/xxxxx",
    "is_email_verified": true,
    "is_active": true,
    "status": "active"
  },
  "is_new_user": true
}
```

**Frontend Callback Handler Example (React/Next.js)**:
```typescript
// pages/auth/google/callback.tsx or app/auth/google/callback/page.tsx

import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

export default function GoogleCallback() {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');
      
      if (!code) {
        router.push('/login?error=no_code');
        return;
      }
      
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/google/callback?code=${code}`
        );
        
        if (!response.ok) {
          throw new Error('Authentication failed');
        }
        
        const data = await response.json();
        
        // Store tokens
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        
        // Store user data
        localStorage.setItem('user', JSON.stringify(data.user));
        
        // Redirect to dashboard
        if (data.is_new_user) {
          router.push('/dashboard?welcome=true');
        } else {
          router.push('/dashboard');
        }
        
      } catch (error) {
        console.error('Google auth error:', error);
        router.push('/login?error=auth_failed');
      }
    };
    
    handleCallback();
  }, [searchParams, router]);
  
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto"></div>
        <p className="mt-4 text-gray-600">Completing sign in...</p>
      </div>
    </div>
  );
}
```

---

### 2.3 Option B: Client-Side OAuth (Using Google Sign-In Button)

If using Google's JavaScript SDK or `@react-oauth/google`:

**Endpoint**: `POST /api/v1/auth/google/token`

**Request Body**:
```json
{
  "id_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response**: Same as callback response above.

**React Example with @react-oauth/google**:
```typescript
import { GoogleLogin } from '@react-oauth/google';

function LoginPage() {
  const handleGoogleSuccess = async (credentialResponse) => {
    try {
      const response = await fetch(`${BASE_URL}/api/v1/auth/google/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id_token: credentialResponse.credential,
        }),
      });
      
      const data = await response.json();
      
      // Store tokens and redirect
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      localStorage.setItem('user', JSON.stringify(data.user));
      
      window.location.href = '/dashboard';
      
    } catch (error) {
      console.error('Login failed:', error);
    }
  };
  
  return (
    <GoogleLogin
      onSuccess={handleGoogleSuccess}
      onError={() => console.log('Login Failed')}
      useOneTap
    />
  );
}
```

---

## 3. Dashboard APIs

### 3.1 Get User Dashboard (Full)

**Endpoint**: `GET /api/v1/dashboards/user`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response**:
```json
{
  "profile": {
    "id": "507f1f77bcf86cd799439011",
    "name": "Victor Asuquo",
    "email": "victor@gmail.com",
    "profile_photo": "https://lh3.googleusercontent.com/a/xxxxx",
    "profile_completion": 75,
    "is_verified": true
  },
  "stats": {
    "total_experiences": 5,
    "upcoming_experiences": 2,
    "total_bookings": 12,
    "total_reviews": 8
  },
  "upcoming_experiences": [...],
  "recent_bookings": [...],
  "notifications": [...],
  "recommendations": [...]
}
```

---

### 3.2 Get User Overview (Quick Stats)

**Endpoint**: `GET /api/v1/dashboards/user/overview`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response**:
```json
{
  "profile": {
    "name": "Victor Asuquo",
    "email": "victor@gmail.com",
    "profile_photo": "https://lh3.googleusercontent.com/a/xxxxx",
    "profile_completion": 75,
    "is_verified": true,
    "member_since": "2025-12-17T10:30:00Z"
  },
  "quick_stats": {
    "experiences": 5,
    "upcoming": 2,
    "bookings": 12,
    "reviews": 8,
    "favorites": 15,
    "followers": 42,
    "following": 38
  },
  "spending": {
    "total_spent": 150000.00,
    "total_saved": 25000.00,
    "currency": "NGN"
  },
  "travel_stats": {
    "countries_visited": 3,
    "cities_visited": 8
  },
  "subscription": {
    "plan": "free",
    "is_active": true,
    "expires_at": null
  },
  "agent": {
    "has_agent": false,
    "agent_id": null
  }
}
```

---

### 3.3 Get User Statistics

**Endpoint**: `GET /api/v1/dashboards/user/stats`

**Headers**:
```
Authorization: Bearer <access_token>
```

---

## 4. User Profile Management

### 4.1 Get Current User Profile

**Endpoint**: `GET /api/v1/users/me`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response**:
```json
{
  "id": "507f1f77bcf86cd799439011",
  "email": "victor@gmail.com",
  "first_name": "Victor",
  "last_name": "Asuquo",
  "full_name": "Victor Asuquo",
  "display_name": null,
  "phone": "+2348012345678",
  "bio": "Travel enthusiast",
  "profile_photo": "https://lh3.googleusercontent.com/a/xxxxx",
  "cover_photo": null,
  "date_of_birth": "1990-05-15",
  "gender": "male",
  "status": "active",
  "is_email_verified": true,
  "is_phone_verified": false,
  "is_active": true,
  "preferences": {
    "interests": ["beaches", "adventure", "culture"],
    "travel_style": "mid-range",
    "dietary_restrictions": [],
    "languages": ["English"],
    "currency": "NGN"
  },
  "notification_preferences": {
    "email_bookings": true,
    "email_promotions": false,
    "push_bookings": true,
    "push_messages": true
  },
  "subscription": {
    "plan": "free",
    "is_active": true,
    "started_at": "2025-12-17T10:30:00Z",
    "expires_at": null
  },
  "followers_count": 42,
  "following_count": 38,
  "experiences_count": 5,
  "reviews_count": 8,
  "favorite_destinations": ["Lagos", "Dubai", "Paris"],
  "referral_code": "QUAB12CD",
  "created_at": "2025-12-17T10:30:00Z",
  "updated_at": "2025-12-17T14:20:00Z",
  "last_login_at": "2025-12-17T14:20:00Z"
}
```

---

### 4.2 Update User Profile

**Endpoint**: `PUT /api/v1/users/me`

**Headers**:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body** (all fields optional):
```json
{
  "first_name": "Victor",
  "last_name": "Asuquo",
  "display_name": "Vic",
  "phone": "+2348012345678",
  "bio": "Travel enthusiast and adventure seeker",
  "date_of_birth": "1990-05-15",
  "gender": "male"
}
```

---

### 4.3 Update Profile Photo

**Endpoint**: `PUT /api/v1/users/me/profile-photo`

**Request Body**:
```json
{
  "profile_photo": "https://cloudinary.com/uploaded-image.jpg"
}
```

---

## 5. Token Management

### 5.1 Refresh Access Token

**Endpoint**: `POST /api/v1/auth/refresh`

**Request Body**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 5.2 Logout

**Endpoint**: `POST /api/v1/auth/logout`

**Response**:
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

## 6. Error Handling

### Error Response Format
```json
{
  "detail": "Error message here"
}
```

### Common HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 400 | Bad Request | Check request body/params |
| 401 | Unauthorized | Token expired/invalid - refresh or re-login |
| 403 | Forbidden | User doesn't have permission |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource already exists (e.g., email taken) |
| 422 | Validation Error | Check field validation requirements |
| 500 | Server Error | Contact support |
| 503 | Service Unavailable | OAuth not configured |

### Auth Error Handling Example
```typescript
const apiCall = async (url: string, options: RequestInit = {}) => {
  const accessToken = localStorage.getItem('access_token');
  
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
  });
  
  if (response.status === 401) {
    // Try to refresh token
    const refreshToken = localStorage.getItem('refresh_token');
    const refreshResponse = await fetch(`${BASE_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    
    if (refreshResponse.ok) {
      const data = await refreshResponse.json();
      localStorage.setItem('access_token', data.access_token);
      
      // Retry original request
      return apiCall(url, options);
    } else {
      // Refresh failed - redirect to login
      localStorage.clear();
      window.location.href = '/login';
    }
  }
  
  return response;
};
```

---

## 7. TypeScript Interfaces

```typescript
// User Types
interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string | null;
  display_name: string | null;
  phone: string | null;
  bio: string | null;
  profile_photo: string | null;
  cover_photo: string | null;
  date_of_birth: string | null;
  gender: string | null;
  status: 'pending' | 'active' | 'suspended' | 'disabled';
  is_email_verified: boolean;
  is_phone_verified: boolean;
  is_active: boolean;
  preferences: UserPreferences | null;
  notification_preferences: NotificationPreferences;
  subscription: UserSubscription | null;
  followers_count: number;
  following_count: number;
  experiences_count: number;
  reviews_count: number;
  favorite_destinations: string[];
  referral_code: string | null;
  assigned_agent_id: string | null;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
}

interface UserPreferences {
  interests: string[];
  travel_style: 'budget' | 'mid-range' | 'luxury' | null;
  dietary_restrictions: string[];
  languages: string[];
  currency: string;
}

interface NotificationPreferences {
  email_bookings: boolean;
  email_promotions: boolean;
  email_newsletter: boolean;
  email_experience_updates: boolean;
  email_agent_messages: boolean;
  push_bookings: boolean;
  push_messages: boolean;
  push_promotions: boolean;
  push_experience_updates: boolean;
  sms_bookings: boolean;
  sms_verification: boolean;
}

interface UserSubscription {
  plan: 'free' | 'basic' | 'premium' | 'enterprise';
  started_at: string;
  expires_at: string | null;
  is_active: boolean;
  auto_renew: boolean;
  features: string[];
}

// Auth Types
interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  expires_in: number;
  user: User;
}

interface GoogleAuthResponse extends LoginResponse {
  is_new_user: boolean;
}

interface RegisterResponse {
  success: boolean;
  message: string;
  user_id: string;
  email: string;
  referral_code: string;
}

// Dashboard Types
interface DashboardOverview {
  profile: {
    name: string;
    email: string;
    profile_photo: string | null;
    profile_completion: number;
    is_verified: boolean;
    member_since: string;
  };
  quick_stats: {
    experiences: number;
    upcoming: number;
    bookings: number;
    reviews: number;
    favorites: number;
    followers: number;
    following: number;
  };
  spending: {
    total_spent: number;
    total_saved: number;
    currency: string;
  };
  travel_stats: {
    countries_visited: number;
    cities_visited: number;
  };
  subscription: {
    plan: string;
    is_active: boolean;
    expires_at: string | null;
  };
  agent: {
    has_agent: boolean;
    agent_id: string | null;
  };
}

// API Error Type
interface ApiError {
  detail: string;
}
```

---

## 8. Complete Implementation Example

### Auth Context (React)
```typescript
// contexts/AuthContext.tsx
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for existing session
    const token = localStorage.getItem('access_token');
    const userData = localStorage.getItem('user');
    
    if (token && userData) {
      setUser(JSON.parse(userData));
    }
    setIsLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/users/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail);
    }

    const data: LoginResponse = await response.json();
    
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    localStorage.setItem('user', JSON.stringify(data.user));
    
    setUser(data.user);
  };

  const loginWithGoogle = async () => {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/google/login`);
    const data = await response.json();
    window.location.href = data.auth_url;
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    setUser(null);
  };

  const refreshUser = async () => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/users/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (response.ok) {
      const userData = await response.json();
      localStorage.setItem('user', JSON.stringify(userData));
      setUser(userData);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        loginWithGoogle,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};
```

### Dashboard Component
```typescript
// components/Dashboard.tsx
import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';

export default function Dashboard() {
  const { user } = useAuth();
  const [overview, setOverview] = useState<DashboardOverview | null>(null);

  useEffect(() => {
    const fetchDashboard = async () => {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/dashboards/user/overview`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (response.ok) {
        setOverview(await response.json());
      }
    };

    fetchDashboard();
  }, []);

  if (!user || !overview) {
    return <div>Loading...</div>;
  }

  return (
    <div className="p-6">
      {/* Welcome Header */}
      <div className="flex items-center gap-4 mb-8">
        <img
          src={user.profile_photo || '/default-avatar.png'}
          alt={user.first_name}
          className="w-16 h-16 rounded-full object-cover"
        />
        <div>
          <h1 className="text-2xl font-bold">
            Welcome back, {user.first_name}! 👋
          </h1>
          <p className="text-gray-600">{user.email}</p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Experiences" value={overview.quick_stats.experiences} />
        <StatCard label="Upcoming" value={overview.quick_stats.upcoming} />
        <StatCard label="Bookings" value={overview.quick_stats.bookings} />
        <StatCard label="Reviews" value={overview.quick_stats.reviews} />
      </div>

      {/* Profile Completion */}
      <div className="bg-white p-4 rounded-lg shadow mb-8">
        <h3 className="font-semibold mb-2">Profile Completion</h3>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-orange-500 h-2 rounded-full"
            style={{ width: `${overview.profile.profile_completion}%` }}
          />
        </div>
        <p className="text-sm text-gray-600 mt-1">
          {overview.profile.profile_completion}% complete
        </p>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-white p-4 rounded-lg shadow">
      <p className="text-gray-600 text-sm">{label}</p>
      <p className="text-2xl font-bold text-orange-500">{value}</p>
    </div>
  );
}
```

---

## 9. Environment Variables (Frontend)

```env
# .env.local
NEXT_PUBLIC_API_URL=https://api.queska.com
NEXT_PUBLIC_GOOGLE_CLIENT_ID=381020104090-xxx.apps.googleusercontent.com
```

---

## 10. Quick Reference

### Authentication Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/users/register` | Register new user |
| POST | `/api/v1/users/login` | Login with email/password |
| GET | `/api/v1/auth/google/login` | Get Google OAuth URL |
| GET | `/api/v1/auth/google/callback?code=xxx` | Handle Google callback |
| POST | `/api/v1/auth/google/token` | Auth with Google ID token |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/auth/logout` | Logout |

### Dashboard Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/dashboards/user` | Full dashboard |
| GET | `/api/v1/dashboards/user/overview` | Quick overview |
| GET | `/api/v1/dashboards/user/stats` | User statistics |

### User Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/users/me` | Get current user |
| PUT | `/api/v1/users/me` | Update profile |
| PUT | `/api/v1/users/me/profile-photo` | Update photo |
| POST | `/api/v1/users/forgot-password` | Request password reset |
| POST | `/api/v1/users/reset-password` | Reset password |
| POST | `/api/v1/users/verify-email/confirm` | Verify email |

---

## Contact

For questions or issues, contact the backend team:
- Email: experiencequeska@gmail.com
- API Docs: https://api.queska.com/docs (when server is running)
