/-
Raw dependency graph of the Stafford38 project, as Lean's environment has it.

Run from a built formal checkout:
  lake env lean --run <supplementary>/scripts/LeanDag.lean <out.json>
For every project constant the output lists its module, its kind and the
constants used by its type and value: project constants under `uses`,
constants of other packages under `external`; `externals` gives the module,
kind and instance-or-projection flag of each of those. scripts/build-lean-dag.py contracts this graph
to the key declarations.
-/
import Stafford38
import Solution
import FixedSourceSolution

open Lean

def projectRoots : List Name :=
  [`Stafford38, `Solution, `FixedSourceSolution, `Challenge, `FixedSourceChallenge, `proofs]

def kind : ConstantInfo → String
  | .thmInfo _ => "theorem" | .defnInfo _ => "def" | .axiomInfo _ => "axiom"
  | .opaqueInfo _ => "opaque" | .inductInfo _ => "inductive" | .ctorInfo _ => "ctor"
  | .recInfo _ => "rec" | .quotInfo _ => "quot"

def main (args : List String) : IO Unit := do
  let [outPath] := args | throw (IO.userError "usage: LeanDag out.json")
  initSearchPath (← findSysroot)
  let env ← importModules #[{ module := `Stafford38 }, { module := `Solution },
    { module := `FixedSourceSolution }] {}
  let modules := env.header.moduleNames
  let moduleOf (c : Name) : Option Name := (env.getModuleIdxFor? c).map (modules[·.toNat]!)
  let isProject (c : Name) : Bool := match moduleOf c with
    | some m => projectRoots.contains m.getRoot
    | none => false
  let mut out : Array (String × Json) := #[]
  let mut seen : NameSet := {}
  for (c, info) in env.constants.toList do
    unless isProject c do continue
    let mut uses : Array Json := #[]
    let mut external : Array Json := #[]
    for d in info.getUsedConstantsAsSet do
      if d == c then continue
      if isProject d then uses := uses.push (Json.str d.toString)
      else
        external := external.push (Json.str d.toString)
        seen := seen.insert d
    out := out.push (c.toString, Json.mkObj [
      ("module", Json.str ((moduleOf c).getD .anonymous).toString),
      ("kind", Json.str (kind info)), ("uses", Json.arr uses), ("external", Json.arr external)])
  -- Instances and structure projections are plumbing, not results used.
  let externals := seen.toList.filterMap fun d => (env.find? d).map fun info =>
    (d.toString, Json.arr #[Json.str ((moduleOf d).getD .anonymous).toString, Json.str (kind info),
      Json.bool (Meta.isInstanceCore env d || env.isProjectionFn d)])
  IO.FS.writeFile outPath (Json.mkObj [("constants", Json.mkObj out.toList),
    ("externals", Json.mkObj externals)]).compress
