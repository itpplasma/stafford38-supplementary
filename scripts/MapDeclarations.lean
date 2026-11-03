/-
Statement fingerprints of given constants, as Lean's environment has them.

Run from a built formal checkout:
  lake env lean --run <supplementary>/scripts/MapDeclarations.lean <modules.txt> <names.txt> <out.json>
Imports the listed modules. A line of names.txt is a constant name, or a
namespace followed by `.*`, which selects every constant under it. For each
constant found the output gives its module, kind, Lean's hash of its type, a
hash of its definition body (definitions) or constructor types (inductive
types), the pretty-printed type, and whether Lean generated it (instances,
projections, recursors, matchers, internal names). scripts/check-map.py
compares two such outputs.
-/
import Lean

open Lean Meta

def kind : ConstantInfo → String
  | .thmInfo _ => "theorem" | .defnInfo _ => "def" | .axiomInfo _ => "axiom"
  | .opaqueInfo _ => "opaque" | .inductInfo _ => "inductive" | .ctorInfo _ => "ctor"
  | .recInfo _ => "rec" | .quotInfo _ => "quot"

def bodyHash (env : Environment) : ConstantInfo → UInt64
  | .defnInfo d => d.value.hash
  | .inductInfo i => i.ctors.foldl (init := 7) fun h c =>
      mixHash h ((env.find? c).map (·.type.hash) |>.getD 0)
  | _ => 0

def generated (env : Environment) (n : Name) (info : ConstantInfo) : Bool :=
  n.isInternalDetail || isPrivateName n || isAuxRecursor env n || isNoConfusion env n ||
    env.isProjectionFn n || Meta.isInstanceCore env n || Meta.isMatcherCore env n ||
    info matches .ctorInfo _ || info matches .recInfo _

def entry (n : Name) (info : ConstantInfo) : MetaM (String × Json) := do
  let env ← getEnv
  let module := (env.getModuleIdxFor? n).map (env.header.moduleNames[·.toNat]!) |>.getD .anonymous
  let shown ← try pure (toString (← ppExpr info.type)) catch _ => pure "<not printable>"
  return (n.toString, Json.mkObj [("module", Json.str module.toString), ("kind", Json.str (kind info)),
    ("type_hash", Json.str (toString info.type.hash)), ("body_hash", Json.str (toString (bodyHash env info))),
    ("generated", Json.bool (generated env n info)), ("type", Json.str shown)])

def main (args : List String) : IO Unit := do
  let [modulesPath, namesPath, outPath] := args
    | throw (IO.userError "usage: MapDeclarations modules.txt names.txt out.json")
  initSearchPath (← findSysroot)
  let modules := ((← IO.FS.lines modulesPath).filter (· ≠ "")).map fun m => { module := m.toName }
  let env ← importModules modules {}
  let lines := (← IO.FS.lines namesPath).filter (· ≠ "")
  let prefixes := (lines.filter (·.endsWith ".*")).map fun l => (String.ofList (l.toList.take (l.length - 2))).toName
  let exact := (lines.filter (!·.endsWith ".*")).map String.toName
  let mut wanted : NameSet := exact.foldl (·.insert ·) {}
  unless prefixes.isEmpty do
    for (c, _) in env.constants.toList do
      if prefixes.any (fun p : Name => p.isPrefixOf c) then wanted := wanted.insert c
  let run : MetaM (Array (String × Json)) :=
    wanted.toList.toArray.filterMapM fun n => do
      match (← getEnv).find? n with
      | some info => return some (← entry n info)
      | none => return none
  let ctx : Core.Context := { fileName := "<map>", fileMap := default, maxHeartbeats := 0 }
  let (entries, _) ← (run.run' {} {} : CoreM _).toIO ctx { env }
  IO.FS.writeFile outPath (Json.mkObj entries.toList).compress
