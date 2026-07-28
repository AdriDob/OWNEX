self.__BUILD_MANIFEST = {
  "__rewrites": {
    "afterFiles": [
      {
        "source": "/chat/completions",
        "destination": "/api/v1/chat/completions"
      },
      {
        "source": "/responses",
        "destination": "/api/v1/responses"
      },
      {
        "source": "/responses/:path*",
        "destination": "/api/v1/responses/:path*"
      },
      {
        "source": "/models",
        "destination": "/api/v1/models"
      },
      {
        "source": "/v1/v1/:path*",
        "destination": "/api/v1/:path*"
      },
      {
        "source": "/v1/v1",
        "destination": "/api/v1"
      },
      {
        "source": "/codex/:path*",
        "destination": "/api/v1/responses"
      },
      {
        "source": "/v1/:path*",
        "destination": "/api/v1/:path*"
      },
      {
        "source": "/v1",
        "destination": "/api/v1"
      },
      {
        "source": "/v1beta/:path*",
        "destination": "/api/v1beta/:path*"
      },
      {
        "source": "/v1beta",
        "destination": "/api/v1beta"
      },
      {
        "source": "/anthropic/:path*",
        "destination": "/api/anthropic/:path*"
      },
      {
        "source": "/openai/:path*",
        "destination": "/api/openai/:path*"
      },
      {
        "source": "/metrics",
        "destination": "/api/metrics"
      },
      {
        "source": "/debug",
        "destination": "/api/debug"
      },
      {
        "source": "/.env",
        "destination": "/api/.env"
      }
    ],
    "beforeFiles": [],
    "fallback": []
  },
  "sortedPages": [
    "/_app",
    "/_error"
  ]
};self.__BUILD_MANIFEST_CB && self.__BUILD_MANIFEST_CB()