"""CLI entrypoint: soulos-studio"""

import argparse
import os


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="soulos-studio",
        description="SoulOS Studio — configure and export .soul.json in your browser",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8765, help="Bind port")
    parser.add_argument(
        "--kernel",
        default=os.getenv("SOULOS_KERNEL_URL", "http://localhost:8000"),
        help="SoulOS kernel URL for deploy & chat test",
    )
    args = parser.parse_args()

    os.environ["SOULOS_KERNEL_URL"] = args.kernel.rstrip("/")

    import uvicorn

    print(f"SoulOS Studio → http://{args.host}:{args.port}")
    print(f"Kernel proxy → {os.environ['SOULOS_KERNEL_URL']}")
    uvicorn.run(
        "soulos_studio.app:app",
        host=args.host,
        port=args.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
