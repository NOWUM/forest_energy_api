# SPDX-FileCopyrightText: 2024 Jonathan Sejdija
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import uvicorn


def main():
    uvicorn.run(
        app="forest_ensys.app:app",
        host="0.0.0.0",
        port=8081,
        log_level="info",
        reload=True,
    )


if __name__ == "__main__":
    main()
