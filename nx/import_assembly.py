# NX journal (NXOpen Python). UNTESTED: written without access to NX.
#
# Imports an aicad assembly.step into a new NX part as an assembly with one
# component per joint part. Run inside NX: Tools > Journal > Play, pick this file,
# then enter the path of assembly.step when asked.
#
# If this script errors on your NX version, the same result by hand:
#   File > Import > STEP214 > choose assembly.step > Import to: New Part > OK
import os

import NXOpen
import NXOpen.UF


def main():
    session = NXOpen.Session.GetSession()
    ui = NXOpen.UI.GetUI()
    step_path = _ask_path(ui)
    if not step_path or not os.path.isfile(step_path):
        ui.NXMessageBox.Show("aicad", NXOpen.NXMessageBox.DialogType.Error, "No assembly.step selected.")
        return
    out_prt = os.path.splitext(step_path)[0] + "_nx.prt"
    importer = session.DexManager.CreateStep214Importer()
    try:
        importer.InputFile = step_path
        importer.OutputFile = out_prt
        importer.ImportTo = NXOpen.Step214Importer.ImportToOption.NewPart
        importer.ObjectTypes.Solids = True
        importer.FileOpenFlag = True
        importer.Commit()
    finally:
        importer.Destroy()
    ui.NXMessageBox.Show("aicad", NXOpen.NXMessageBox.DialogType.Information,
                         "Imported " + step_path + " into " + out_prt)


def _ask_path(ui):
    import NXOpen.UF as UF
    uf = UF.UFSession.GetUFSession()
    resp, name = uf.Ui.CreateFilebox("*.step", "Choose aicad assembly.step", "", "", "")
    return name if resp == 1 else None


if __name__ == "__main__":
    main()
