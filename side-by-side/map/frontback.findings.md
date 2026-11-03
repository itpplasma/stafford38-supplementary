# Paper findings: abstract, Sections 1, 2, 7 and 8

Paper: itpplasma/stafford38-paper, `human_readable_main.tex` at c8f0d615ba3ad7271c1c99ad4b0085071da6a793.
Lean: itpplasma/stafford38-formal at 665fb5bbd26967bfde5c9c30f27513f4cea37f24.
The paper is not edited; each finding names the card of `frontback.json`.

## 1. Non-holonomic torsion modules need no construction (card `lit:holonomic`)

Paper: "However, torsion modules need not be holonomic: for $n\ge2$, Stafford constructed quotients
$A_n(k)/dA_n(k)$ of Gelfand--Kirillov dimension $2n-1$ as counterexamples \cite{StaffordNonholonomic1985}"

Lean: none (literature).

Why: for every nonzero non-unit $d$ the characteristic variety of $A_n(k)/dA_n(k)$ is the hypersurface
$V(\sigma(d))$, so its dimension is $2n-1>n$ for $n\ge2$ and every such quotient is non-holonomic. The point
of the cited Inventiones paper is that some of these quotients are simple. As written, the sentence presents a
standard fact as a construction, and "simple" (or "irreducible") seems to be missing. Status: the dimension
count is standard; what the cited paper constructs is a hypothesis from its title and the usual citation.

## 2. Left torsion module and right ideal (card `lit:dixmier`)

Paper: "moreover showed, that any finitely generated left torsion $A_n(k)$-module is isomorphic to a right
ideal"

Lean: none (literature).

Why: a left module can be isomorphic to a left ideal, not to a right ideal; the sides look mixed. Not checked
against \cite[Theorem 3.7]{Stafford1978}. Status: hypothesis.

## 3. The Lean reference under Theorem 1.1 names a different assembly (card `thm:main`)

Paper: `\leandecl{Stafford38/FoundationClosure.lean}{67}{Stafford38.universalStatement} proves
\leandecl{Stafford38/Statement.lean}{23}{Stafford38.UniversalStatement}`

Lean: `Stafford38.universalStatement` (FoundationClosure.lean:67) is
`UniversalAssembly.universalStatement_of_canonicalSupportVanishing
FoundationClosure.canonicalSupportVanishingViaGeneralCoisotropic`; the compared theorem
`Stafford38Challenge.universalStatement` (Solution.lean) is `Stafford38.Paper.theorem_1_1`
(Stafford38/Paper/Main.lean:24, `Section6.theorem_1_1_paper`).

Why: Section 1.2 says the printed proof "follows the formal proof step by step", and that holds for the
`Stafford38.Paper` route mapped in this reader; the declaration the paper itself cites below Theorem 1.1 is a
separate assembly that no file under `Stafford38/Paper/` or `Solution.lean` uses (checked by search at the pinned
commit). Status: verified.

## 4. The appendix still says the review is in progress (card `ai:rewrite`)

Paper: "The authors are reviewing this correspondence and revising the text for clarity together with the
agents, until both the human review and the AI checks raise no further objections."

Lean: none.

Why: commit c8f0d61 ("Remove the pending-review statements: both human reviews are complete") changes only
README.md; the manuscript keeps the present-tense statement. Status: verified that the sentence is unchanged at
c8f0d61; whether it should change is the authors' call.

## 5. Generalization (b) rests on a placeholder citation (card `gen:further`)

Paper: "For all nonzero $d,a\in U$ and every $B\in U$ there are $H,R,S\in U$ with $1=dR+(B+Ha)dS$
\cite{SameDivisorFiltered}", with `\AIcomment{FV-03}{... its citation is a placeholder until the manuscript and
archive exist.}`

Lean: not in this formalization; the paper links symplectic-stafford-formal at dccff0d.

Why: the bibliography entry `SameDivisorFiltered` is "In preparation", and the placeholder comment is still in
the final manuscript. The claim "also proved in Lean" is not checkable from this reader. Status: verified that
the entry and the comment are present at c8f0d61.

## 6. "Every nonzero d" in the quotation of Conjecture 3.8 (card `intro:conjecture`)

Paper: "Stafford's Conjecture~3.8 in \cite{Stafford1978} asks whether every nonzero $d\in A_n(k)$ admits ..."

Lean: `Stafford38Challenge.UniversalStatement` requires `d ≠ 0`; the Challenge.lean header says the printed
conjecture omits this hypothesis, which the discussion after it uses.

Why: if the header is right, the paper puts the nonzero form into Stafford's mouth without saying so. Minor.
Status: hypothesis (not checked against Stafford 1978).
