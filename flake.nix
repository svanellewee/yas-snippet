{
  description = "yas-snippet: A smooth, cross-platform screenshot annotator";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, utils }:
    utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        
        pythonEnv = pkgs.python3.withPackages (ps: with ps; [
          pillow
          tkinter
        ]);

        runtimeDeps = if pkgs.stdenv.isDarwin 
                      then [] 
                      else [ pkgs.grim pkgs.slurp pkgs.wl-clipboard ];

        # Create the desktop entry for Linux launchers
        desktopItem = pkgs.makeDesktopItem {
          name = "yas-snippet";
          exec = "yas-snippet";
          icon = "camera-photo";
          desktopName = "YAS Snippet";
          genericName = "Screenshot Annotator";
          categories = [ "Utility" "Graphics" ];
        };

        yas-snippet = pkgs.writeShellScriptBin "yas-snippet" ''
          export PATH="${pkgs.lib.makeBinPath runtimeDeps}:$PATH"
          ${pythonEnv}/bin/python3 ${./main.py}
        '';
      in
      {
        packages.default = pkgs.symlinkJoin {
          name = "yas-snippet";
          paths = [ yas-snippet desktopItem ];
        };

        apps.default = {
          type = "app";
          program = "${yas-snippet}/bin/yas-snippet";
        };

        devShells.default = pkgs.mkShell {
          buildInputs = [ pythonEnv ] ++ runtimeDeps;
        };
      });
}
