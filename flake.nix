{
  description = "Dublin rainfall forecasting — ML model + Three.js terrain visualization";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };
      in
      {
        devShells.default = pkgs.mkShell {
          packages = [
            pkgs.python311
            pkgs.uv
            pkgs.nodejs_22
            pkgs.git
          ];

          shellHook = ''
            # ML wheels (numpy, tensorflow, torch, etc.) need to find system C libraries
            export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib:${pkgs.zlib}/lib:$LD_LIBRARY_PATH

            # Tell uv to use the Nix-provided Python rather than downloading its own
            export UV_PYTHON_PREFERENCE=only-system
            export UV_PYTHON=${pkgs.python311}/bin/python3.11

            echo ""
            echo "  Dublin rainfall dev shell ready."
            echo "  Python: $(python3 --version)   uv: $(uv --version)   Node: $(node --version)"
            echo ""
            echo "  First time:   uv sync"
            echo "  Run a script: uv run python train.py"
            echo "  Serve 3D:     python3 -m http.server 8000"
            echo ""
          '';
        };
      });
}