from rdkit import Chem
from functools import partial

from guacamol_local.common_scoring_functions import TanimotoScoringFunction, RdkitScoringFunction, CNS_MPO_ScoringFunction, \
    IsomerScoringFunction, SMARTSScoringFunction
from guacamol_local.distribution_learning_benchmark import DistributionLearningBenchmark, NoveltyBenchmark, KLDivBenchmark
from guacamol_local.frechet_benchmark import FrechetBenchmark
from guacamol_local.goal_directed_benchmark import GoalDirectedBenchmark
from guacamol_local.goal_directed_score_contributions import uniform_specification
from guacamol_local.score_modifier import MinGaussianModifier, MaxGaussianModifier, ClippedScoreModifier, GaussianModifier
from guacamol_local.scoring_function import ArithmeticMeanScoringFunction, GeometricMeanScoringFunction, ScoringFunction, \
    ScoringFunctionSAWrapper
from guacamol_local.utils.descriptors import num_rotatable_bonds, num_aromatic_rings, logP, qed, tpsa, bertz, mol_weight, \
    AtomCounter, num_rings
from guacamol_local.sa_modifier import LinearModifier, SAScoreModifier, SCScoreModifier, SmilesModifier


def isomers_c11h24(mean_function='geometric') -> GoalDirectedBenchmark:
    """
    Benchmark to try and get all C11H24 molecules there are.
    There should be 159 if one ignores stereochemistry.

    Args:
        mean_function: 'arithmetic' or 'geometric'
    """

    specification = uniform_specification(159)

    return GoalDirectedBenchmark(name='C11H24',
                                 objective=IsomerScoringFunction('C11H24', mean_function=mean_function),
                                 contribution_specification=specification)


def isomers_c7h8n2o2(mean_function='geometric') -> GoalDirectedBenchmark:
    """
    Benchmark to try and get 100 isomers for C7H8N2O2.

    Args:
        mean_function: 'arithmetic' or 'geometric'
    """

    specification = uniform_specification(100)

    return GoalDirectedBenchmark(name='C7H8N2O2',
                                 objective=IsomerScoringFunction('C7H8N2O2', mean_function=mean_function),
                                 contribution_specification=specification)


def isomers_c9h10n2o2pf2cl(mean_function='geometric', n_samples=250) -> GoalDirectedBenchmark:
    """
    Benchmark to try and get 100 isomers for C9H10N2O2PF2Cl.

    Args:
        mean_function: 'arithmetic' or 'geometric'
    """

    specification = uniform_specification(n_samples)

    return GoalDirectedBenchmark(name='C9H10N2O2PF2Cl',
                                 objective=IsomerScoringFunction('C9H10N2O2PF2Cl', mean_function=mean_function),
                                 contribution_specification=specification)


def hard_cobimetinib(max_logP=5.0) -> GoalDirectedBenchmark:
    smiles = 'OC1(CN(C1)C(=O)C1=C(NC2=C(F)C=C(I)C=C2)C(F)=C(F)C=C1)C1CCCCN1'

    modifier = ClippedScoreModifier(upper_x=0.7)
    os_tf = TanimotoScoringFunction(smiles, fp_type='FCFP4', score_modifier=modifier)
    os_ap = TanimotoScoringFunction(smiles, fp_type='ECFP6',
                                    score_modifier=MinGaussianModifier(mu=0.75, sigma=0.1))

    rot_b = RdkitScoringFunction(descriptor=num_rotatable_bonds,
                                 score_modifier=MinGaussianModifier(mu=3, sigma=1))

    rings = RdkitScoringFunction(descriptor=num_aromatic_rings,
                                 score_modifier=MaxGaussianModifier(mu=3, sigma=1))

    t_cns = ArithmeticMeanScoringFunction([os_tf, os_ap, rot_b, rings, CNS_MPO_ScoringFunction(max_logP=max_logP)])

    specification = uniform_specification(1, 10, 100)

    return GoalDirectedBenchmark(name='Cobimetinib MPO',
                                 objective=t_cns,
                                 contribution_specification=specification)


def hard_osimertinib(mean_cls=GeometricMeanScoringFunction) -> GoalDirectedBenchmark:
    smiles = 'COc1cc(N(C)CCN(C)C)c(NC(=O)C=C)cc1Nc2nccc(n2)c3cn(C)c4ccccc34'

    modifier = ClippedScoreModifier(upper_x=0.8)
    similar_to_osimertinib = TanimotoScoringFunction(smiles, fp_type='FCFP4', score_modifier=modifier)

    but_not_too_similar = TanimotoScoringFunction(smiles, fp_type='ECFP6',
                                                  score_modifier=MinGaussianModifier(mu=0.85, sigma=0.1))

    tpsa_over_100 = RdkitScoringFunction(descriptor=tpsa,
                                         score_modifier=MaxGaussianModifier(mu=100, sigma=10))

    logP_scoring = RdkitScoringFunction(descriptor=logP,
                                        score_modifier=MinGaussianModifier(mu=1, sigma=1))

    make_osimertinib_great_again = mean_cls(
        [similar_to_osimertinib, but_not_too_similar, tpsa_over_100, logP_scoring])

    specification = uniform_specification(1, 10, 100)

    return GoalDirectedBenchmark(name='Osimertinib MPO',
                                 objective=make_osimertinib_great_again,
                                 contribution_specification=specification)

def sa_hard_osimertinib() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = hard_osimertinib()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SAScoreModifier())
    return GoalDirectedBenchmark(name='SA_osimertinib',
                                 objective=sa_biased,
                                 contribution_specification=specification)

def sc_hard_osimertinib() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = hard_osimertinib()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SCScoreModifier())
    return GoalDirectedBenchmark(name='SC_osimertinib',
                                 objective=sa_biased,
                                 contribution_specification=specification)


def hard_fexofenadine(mean_cls=GeometricMeanScoringFunction) -> GoalDirectedBenchmark:
    """
    make fexofenadine less greasy
    :return:
    """
    smiles = 'CC(C)(C(=O)O)c1ccc(cc1)C(O)CCCN2CCC(CC2)C(O)(c3ccccc3)c4ccccc4'

    modifier = ClippedScoreModifier(upper_x=0.8)
    similar_to_fexofenadine = TanimotoScoringFunction(smiles, fp_type='AP', score_modifier=modifier)

    tpsa_over_90 = RdkitScoringFunction(descriptor=tpsa,
                                        score_modifier=MaxGaussianModifier(mu=90, sigma=10))

    logP_under_4 = RdkitScoringFunction(descriptor=logP,
                                        score_modifier=MinGaussianModifier(mu=4, sigma=1))

    optimize_fexofenadine = mean_cls(
        [similar_to_fexofenadine, tpsa_over_90, logP_under_4])

    specification = uniform_specification(1, 10, 100)

    return GoalDirectedBenchmark(name='Fexofenadine MPO',
                                 objective=optimize_fexofenadine,
                                 contribution_specification=specification)

def sa_hard_fexofenadine() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = hard_fexofenadine()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SAScoreModifier())
    return GoalDirectedBenchmark(name='SA_fexofenadine',
                                 objective=sa_biased,
                                 contribution_specification=specification)

def sc_hard_fexofenadine() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = hard_fexofenadine()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SCScoreModifier())
    return GoalDirectedBenchmark(name='SC_fexofenadine',
                                 objective=sa_biased,
                                 contribution_specification=specification)


def start_pop_ranolazine() -> GoalDirectedBenchmark:
    ranolazine = 'COc1ccccc1OCC(O)CN2CCN(CC(=O)Nc3c(C)cccc3C)CC2'

    modifier = ClippedScoreModifier(upper_x=0.7)
    similar_to_ranolazine = TanimotoScoringFunction(ranolazine, fp_type='AP', score_modifier=modifier)

    logP_under_4 = RdkitScoringFunction(descriptor=logP,
                                        score_modifier=MaxGaussianModifier(mu=7, sigma=1))

    aroma = RdkitScoringFunction(descriptor=num_aromatic_rings,
                                 score_modifier=MinGaussianModifier(mu=1, sigma=1))

    fluorine = RdkitScoringFunction(descriptor=AtomCounter('F'),
                                    score_modifier=GaussianModifier(mu=1, sigma=1.0))

    optimize_ranolazine = ArithmeticMeanScoringFunction([similar_to_ranolazine, logP_under_4, fluorine, aroma])

    specification = uniform_specification(1, 10, 100)

    return GoalDirectedBenchmark(name='Ranolazine MPO',
                                 objective=optimize_ranolazine,
                                 contribution_specification=specification,
                                 starting_population=[ranolazine])

def sa_ranolazine() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = start_pop_ranolazine()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SAScoreModifier())
    return GoalDirectedBenchmark(name='SA_ranolazine',
                                 objective=sa_biased,
                                 contribution_specification=specification)

def sc_ranolazine() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = start_pop_ranolazine()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SCScoreModifier())
    return GoalDirectedBenchmark(name='SC_ranolazine',
                                 objective=sa_biased,
                                 contribution_specification=specification)


def weird_physchem() -> GoalDirectedBenchmark:
    min_bertz = RdkitScoringFunction(descriptor=bertz,
                                     score_modifier=MaxGaussianModifier(mu=1500, sigma=200))

    mol_under_400 = RdkitScoringFunction(descriptor=mol_weight,
                                         score_modifier=MinGaussianModifier(mu=400, sigma=40))

    aroma = RdkitScoringFunction(descriptor=num_aromatic_rings,
                                 score_modifier=MinGaussianModifier(mu=3, sigma=1))

    fluorine = RdkitScoringFunction(descriptor=AtomCounter('F'),
                                    score_modifier=GaussianModifier(mu=6, sigma=1.0))

    opt_weird = ArithmeticMeanScoringFunction(
        [min_bertz, mol_under_400, aroma, fluorine])

    specification = uniform_specification(1, 10, 100)

    return GoalDirectedBenchmark(name='Physchem MPO',
                                 objective=opt_weird,
                                 contribution_specification=specification)


def similarity_cns_mpo(smiles, molecule_name, max_logP=5.0) -> GoalDirectedBenchmark:
    benchmark_name = f'{molecule_name}'
    os_tf = TanimotoScoringFunction(smiles, fp_type='FCFP4')
    os_ap = TanimotoScoringFunction(smiles, fp_type='AP')
    anti_fp = TanimotoScoringFunction(smiles, fp_type='ECFP6',
                                      score_modifier=MinGaussianModifier(mu=0.70, sigma=0.1))

    t_cns = ArithmeticMeanScoringFunction([os_tf, os_ap, anti_fp, CNS_MPO_ScoringFunction(max_logP=max_logP)])

    specification = uniform_specification(1, 10, 100)

    return GoalDirectedBenchmark(name=benchmark_name,
                                 objective=t_cns,
                                 contribution_specification=specification)


def similarity(smiles: str, name: str, fp_type: str = 'ECFP4', threshold: float = 0.7,
               rediscovery: bool = False) -> GoalDirectedBenchmark:
    category = 'rediscovery' if rediscovery else 'similarity'
    benchmark_name = f'{name} {category}'

    modifier = ClippedScoreModifier(upper_x=threshold)
    scoring_function = TanimotoScoringFunction(target=smiles, fp_type=fp_type, score_modifier=modifier)
    if rediscovery:
        specification = uniform_specification(1)
    else:
        specification = uniform_specification(1, 10, 100)

    return GoalDirectedBenchmark(name=benchmark_name,
                                 objective=scoring_function,
                                 contribution_specification=specification)


def logP_benchmark(target: float) -> GoalDirectedBenchmark:
    benchmark_name = f'logP (target: {target})'
    objective = RdkitScoringFunction(descriptor=logP,
                                     score_modifier=GaussianModifier(mu=target, sigma=1))

    specification = uniform_specification(1, 10, 100)

    return GoalDirectedBenchmark(name=benchmark_name,
                                 objective=objective,
                                 contribution_specification=specification)

def sa_logp_target(target: float) -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = logP_benchmark(target)
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SAScoreModifier())
    return GoalDirectedBenchmark(name='SA_logP_target',
                                 objective=sa_biased,
                                 contribution_specification=specification)


def tpsa_benchmark(target: float) -> GoalDirectedBenchmark:
    benchmark_name = f'TPSA (target: {target})'
    objective = RdkitScoringFunction(descriptor=tpsa,
                                     score_modifier=GaussianModifier(mu=target, sigma=20.0))

    specification = uniform_specification(1, 10, 100)

    return GoalDirectedBenchmark(name=benchmark_name,
                                 objective=objective,
                                 contribution_specification=specification)


def cns_mpo(max_logP=5.0) -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    return GoalDirectedBenchmark(name='CNS MPO', objective=CNS_MPO_ScoringFunction(max_logP=max_logP),
                                 contribution_specification=specification)


def qed_benchmark() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    return GoalDirectedBenchmark(name='QED',
                                 objective=RdkitScoringFunction(descriptor=qed),
                                 contribution_specification=specification)


def median_camphor_menthol(mean_cls=GeometricMeanScoringFunction) -> GoalDirectedBenchmark:
    t_camphor = TanimotoScoringFunction('CC1(C)C2CCC1(C)C(=O)C2', fp_type='ECFP4')
    t_menthol = TanimotoScoringFunction('CC(C)C1CCC(C)CC1O', fp_type='ECFP4')
    median = mean_cls([t_menthol, t_camphor])

    specification = uniform_specification(1, 10, 100)

    return GoalDirectedBenchmark(name='Median molecules 1',
                                 objective=median,
                                 contribution_specification=specification)

def sa_median1() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = median_camphor_menthol()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SAScoreModifier())
    return GoalDirectedBenchmark(name='SA_median1',
                                 objective=sa_biased,
                                 contribution_specification=specification)


def novelty_benchmark(training_set_file: str, number_samples: int) -> DistributionLearningBenchmark:
    smiles_list = [s.strip() for s in open(training_set_file).readlines()]
    return NoveltyBenchmark(number_samples=number_samples, training_set=smiles_list)


def kldiv_benchmark(training_set_file: str, number_samples: int) -> DistributionLearningBenchmark:
    smiles_list = [s.strip() for s in open(training_set_file).readlines()]
    return KLDivBenchmark(number_samples=number_samples, training_set=smiles_list)


def frechet_benchmark(training_set_file: str, number_samples: int) -> DistributionLearningBenchmark:
    smiles_list = [s.strip() for s in open(training_set_file).readlines()]
    return FrechetBenchmark(training_set=smiles_list, sample_size=number_samples)


def perindopril_rings() -> GoalDirectedBenchmark:
    # perindopril with two aromatic rings
    perindopril = TanimotoScoringFunction('O=C(OCC)C(NC(C(=O)N1C(C(=O)O)CC2CCCCC12)C)CCC',
                                          fp_type='ECFP4')
    arom_rings = RdkitScoringFunction(descriptor=num_aromatic_rings,
                                      score_modifier=GaussianModifier(mu=2, sigma=0.5))

    specification = uniform_specification(1, 10, 100)

    return GoalDirectedBenchmark(name='Perindopril MPO',
                                 objective=GeometricMeanScoringFunction([perindopril, arom_rings]),
                                 contribution_specification=specification)

def sa_perindopril_rings() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = perindopril_rings()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SAScoreModifier())
    return GoalDirectedBenchmark(name='SA_perindopril',
                                 objective=sa_biased,
                                 contribution_specification=specification)

def sc_perindopril_rings() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = perindopril_rings()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SCScoreModifier())
    return GoalDirectedBenchmark(name='SC_perindopril',
                                 objective=sa_biased,
                                 contribution_specification=specification)


def amlodipine_rings() -> GoalDirectedBenchmark:
    # amlodipine with 3 rings
    amlodipine = TanimotoScoringFunction(r'Clc1ccccc1C2C(=C(/N/C(=C2/C(=O)OCC)COCCN)C)\C(=O)OC', fp_type='ECFP4')
    rings = RdkitScoringFunction(descriptor=num_rings,
                                 score_modifier=GaussianModifier(mu=3, sigma=0.5))

    specification = uniform_specification(1, 10, 100)

    return GoalDirectedBenchmark(name='Amlodipine MPO',
                                 objective=GeometricMeanScoringFunction([amlodipine, rings]),
                                 contribution_specification=specification)

def sa_amlodipine_rings() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = amlodipine_rings()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SAScoreModifier())
    return GoalDirectedBenchmark(name='SA_amlodipine',
                                 objective=sa_biased,
                                 contribution_specification=specification)

def sc_amlodipine_rings() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = amlodipine_rings()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SCScoreModifier())
    return GoalDirectedBenchmark(name='SC_amlodipine',
                                 objective=sa_biased,
                                 contribution_specification=specification)


def sitagliptin_replacement() -> GoalDirectedBenchmark:
    # Find a molecule dissimilar to sitagliptin, but with the same properties
    smiles = 'Fc1cc(c(F)cc1F)CC(N)CC(=O)N3Cc2nnc(n2CC3)C(F)(F)F'
    sitagliptin = Chem.MolFromSmiles(smiles)
    target_logp = logP(sitagliptin)
    target_tpsa = tpsa(sitagliptin)

    similarity = TanimotoScoringFunction(smiles, fp_type='ECFP4',
                                         score_modifier=GaussianModifier(mu=0, sigma=0.1))
    lp = RdkitScoringFunction(descriptor=logP,
                              score_modifier=GaussianModifier(mu=target_logp, sigma=0.2))
    tp = RdkitScoringFunction(descriptor=tpsa,
                              score_modifier=GaussianModifier(mu=target_tpsa, sigma=5))
    isomers = IsomerScoringFunction('C16H15F6N5O')

    specification = uniform_specification(1, 10, 100)

    return GoalDirectedBenchmark(name='Sitagliptin MPO',
                                 objective=GeometricMeanScoringFunction([similarity, lp, tp, isomers]),
                                 contribution_specification=specification)

def sa_sitagliptin_replacement() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = sitagliptin_replacement()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SAScoreModifier())
    return GoalDirectedBenchmark(name='SA_sitagliptin',
                                 objective=sa_biased,
                                 contribution_specification=specification)

def sc_sitagliptin_replacement() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = sitagliptin_replacement()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SCScoreModifier())
    return GoalDirectedBenchmark(name='SC_sitagliptin',
                                 objective=sa_biased,
                                 contribution_specification=specification)


def zaleplon_with_other_formula() -> GoalDirectedBenchmark:
    # zaleplon_with_other_formula with other formula
    zaleplon = TanimotoScoringFunction('O=C(C)N(CC)C1=CC=CC(C2=CC=NC3=C(C=NN23)C#N)=C1',
                                       fp_type='ECFP4')
    formula = IsomerScoringFunction('C19H17N3O2')

    specification = uniform_specification(1, 10, 100)

    return GoalDirectedBenchmark(name='Zaleplon MPO',
                                 objective=GeometricMeanScoringFunction([zaleplon, formula]),
                                 contribution_specification=specification)

def sa_zaleplon_with_other_formula() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = zaleplon_with_other_formula()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SAScoreModifier())
    return GoalDirectedBenchmark(name='SA_zaleplon',
                                 objective=sa_biased,
                                 contribution_specification=specification)

def sc_zaleplon_with_other_formula() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = zaleplon_with_other_formula()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SCScoreModifier())
    return GoalDirectedBenchmark(name='SC_zaleplon',
                                 objective=sa_biased,
                                 contribution_specification=specification)


def smarts_with_other_target(smarts: str, other_molecule: str) -> ScoringFunction:
    smarts_scoring_function = SMARTSScoringFunction(target=smarts)
    other_mol = Chem.MolFromSmiles(other_molecule)
    target_logp = logP(other_mol)
    target_tpsa = tpsa(other_mol)
    target_bertz = bertz(other_mol)

    lp = RdkitScoringFunction(descriptor=logP,
                              score_modifier=GaussianModifier(mu=target_logp, sigma=0.2))
    tp = RdkitScoringFunction(descriptor=tpsa,
                              score_modifier=GaussianModifier(mu=target_tpsa, sigma=5))
    bz = RdkitScoringFunction(descriptor=bertz,
                              score_modifier=GaussianModifier(mu=target_bertz, sigma=30))

    return GeometricMeanScoringFunction([smarts_scoring_function, lp, tp, bz])


def valsartan_smarts() -> GoalDirectedBenchmark:
    # valsartan smarts with sitagliptin properties
    sitagliptin_smiles = 'NC(CC(=O)N1CCn2c(nnc2C(F)(F)F)C1)Cc1cc(F)c(F)cc1F'
    valsartan_smarts = 'CN(C=O)Cc1ccc(c2ccccc2)cc1'
    specification = uniform_specification(1, 10, 100)
    return GoalDirectedBenchmark(name='Valsartan SMARTS',
                                 objective=smarts_with_other_target(valsartan_smarts, sitagliptin_smiles),
                                 contribution_specification=specification)

def sa_valsartan_smarts() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = valsartan_smarts()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SAScoreModifier())
    return GoalDirectedBenchmark(name='SA_valsartan',
                                 objective=sa_biased,
                                 contribution_specification=specification)

def sc_valsartan_smarts() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = valsartan_smarts()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SCScoreModifier())
    return GoalDirectedBenchmark(name='SC_valsartan',
                                 objective=sa_biased,
                                 contribution_specification=specification)


def median_tadalafil_sildenafil() -> GoalDirectedBenchmark:
    # median mol between tadalafil and sildenafil
    m1 = TanimotoScoringFunction('O=C1N(CC(N2C1CC3=C(C2C4=CC5=C(OCO5)C=C4)NC6=C3C=CC=C6)=O)C', fp_type='ECFP6')
    m2 = TanimotoScoringFunction('CCCC1=NN(C2=C1N=C(NC2=O)C3=C(C=CC(=C3)S(=O)(=O)N4CCN(CC4)C)OCC)C', fp_type='ECFP6')
    median = GeometricMeanScoringFunction([m1, m2])

    specification = uniform_specification(1, 10, 100)

    return GoalDirectedBenchmark(name='Median molecules 2',
                                 objective=median,
                                 contribution_specification=specification)

def sa_median_tadalafil_sildenafil() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = median_tadalafil_sildenafil()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SAScoreModifier())
    return GoalDirectedBenchmark(name='SA_median2',
                                 objective=sa_biased,
                                 contribution_specification=specification)


def pioglitazone_mpo() -> GoalDirectedBenchmark:
    # pioglitazone with same mw but less rotatable bonds
    smiles = 'O=C1NC(=O)SC1Cc3ccc(OCCc2ncc(cc2)CC)cc3'
    pioglitazone = Chem.MolFromSmiles(smiles)
    target_molw = mol_weight(pioglitazone)

    similarity = TanimotoScoringFunction(smiles, fp_type='ECFP4',
                                         score_modifier=GaussianModifier(mu=0, sigma=0.1))
    mw = RdkitScoringFunction(descriptor=mol_weight,
                              score_modifier=GaussianModifier(mu=target_molw, sigma=10))
    rb = RdkitScoringFunction(descriptor=num_rotatable_bonds,
                              score_modifier=GaussianModifier(mu=2, sigma=0.5))

    specification = uniform_specification(1, 10, 100)

    return GoalDirectedBenchmark(name='Pioglitazone MPO',
                                 objective=GeometricMeanScoringFunction([similarity, mw, rb]),
                                 contribution_specification=specification)


def decoration_hop() -> GoalDirectedBenchmark:
    smiles = 'CCCOc1cc2ncnc(Nc3ccc4ncsc4c3)c2cc1S(=O)(=O)C(C)(C)C'

    pharmacophor_sim = TanimotoScoringFunction(smiles, fp_type='PHCO',
                                               score_modifier=ClippedScoreModifier(upper_x=0.85))
    # change deco
    deco1 = SMARTSScoringFunction('CS([#6])(=O)=O', inverse=True)
    deco2 = SMARTSScoringFunction('[#7]-c1ccc2ncsc2c1', inverse=True)

    # keep scaffold
    scaffold = SMARTSScoringFunction('[#7]-c1n[c;h1]nc2[c;h1]c(-[#8])[c;h0][c;h1]c12', inverse=False)

    deco_hop1_fn = ArithmeticMeanScoringFunction([pharmacophor_sim, deco1, deco2, scaffold])

    specification = uniform_specification(1, 10, 100)

    return GoalDirectedBenchmark(name='Deco Hop',
                                 objective=deco_hop1_fn,
                                 contribution_specification=specification)

def sa_decoration_hop() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = decoration_hop()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SAScoreModifier())
    return GoalDirectedBenchmark(name='SA_decoration_hop',
                                 objective=sa_biased,
                                 contribution_specification=specification)

def sc_decoration_hop() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = decoration_hop()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SCScoreModifier())
    return GoalDirectedBenchmark(name='SC_decoration_hop',
                                 objective=sa_biased,
                                 contribution_specification=specification)


def scaffold_hop() -> GoalDirectedBenchmark:
    """
    Keep the decoration, and similarity to start point, but change the scaffold.
    """

    smiles = 'CCCOc1cc2ncnc(Nc3ccc4ncsc4c3)c2cc1S(=O)(=O)C(C)(C)C'

    pharmacophor_sim = TanimotoScoringFunction(smiles, fp_type='PHCO',
                                               score_modifier=ClippedScoreModifier(upper_x=0.75))

    deco = SMARTSScoringFunction('[#6]-[#6]-[#6]-[#8]-[#6]~[#6]~[#6]~[#6]~[#6]-[#7]-c1ccc2ncsc2c1', inverse=False)

    # anti scaffold
    scaffold = SMARTSScoringFunction('[#7]-c1n[c;h1]nc2[c;h1]c(-[#8])[c;h0][c;h1]c12', inverse=True)

    scaffold_hop_obj = ArithmeticMeanScoringFunction([pharmacophor_sim, deco, scaffold])

    specification = uniform_specification(1, 10, 100)

    return GoalDirectedBenchmark(name='Scaffold Hop',
                                 objective=scaffold_hop_obj,
                                 contribution_specification=specification)

def sa_scaffold_hop() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = scaffold_hop()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SAScoreModifier())
    return GoalDirectedBenchmark(name='SA_scaffold_hop',
                                 objective=sa_biased,
                                 contribution_specification=specification)

def sc_scaffold_hop() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = scaffold_hop()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SCScoreModifier())
    return GoalDirectedBenchmark(name='SC_scaffold_hop',
                                 objective=sa_biased,
                                 contribution_specification=specification)


def ranolazine_mpo() -> GoalDirectedBenchmark:
    """
    Make start_pop_ranolazine more polar and add a fluorine
    """
    ranolazine = 'COc1ccccc1OCC(O)CN2CCN(CC(=O)Nc3c(C)cccc3C)CC2'

    modifier = ClippedScoreModifier(upper_x=0.7)
    similar_to_ranolazine = TanimotoScoringFunction(ranolazine, fp_type='AP', score_modifier=modifier)

    logP_under_4 = RdkitScoringFunction(descriptor=logP, score_modifier=MaxGaussianModifier(mu=7, sigma=1))

    tpsa_f = RdkitScoringFunction(descriptor=tpsa, score_modifier=MaxGaussianModifier(mu=95, sigma=20))

    fluorine = RdkitScoringFunction(descriptor=AtomCounter('F'), score_modifier=GaussianModifier(mu=1, sigma=1.0))

    optimize_ranolazine = GeometricMeanScoringFunction([similar_to_ranolazine, logP_under_4, fluorine, tpsa_f])

    specification = uniform_specification(1, 10, 100)

    return GoalDirectedBenchmark(name='Ranolazine MPO',
                                 objective=optimize_ranolazine,
                                 contribution_specification=specification,
                                 starting_population=[ranolazine])


def sa_qed_benchmark() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    sa_qed = ScoringFunctionSAWrapper(RdkitScoringFunction(descriptor=qed), SAScoreModifier())
    return GoalDirectedBenchmark(name='SA_QED',
                                 objective=sa_qed,
                                 contribution_specification=specification)

def sa_ranolazine_mpo() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = ranolazine_mpo()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SAScoreModifier())
    return GoalDirectedBenchmark(name='SA_ranolazine',
                                 objective=sa_biased,
                                 contribution_specification=specification)

def sa_cns_mpo() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = cns_mpo()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SAScoreModifier())
    return GoalDirectedBenchmark(name='SA_CNS',
                                 objective=sa_biased,
                                 contribution_specification=specification)

def sa_isomers_c7h8n2o2() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = isomers_c7h8n2o2()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SAScoreModifier())
    return GoalDirectedBenchmark(name='SA_isomer',
                                 objective=sa_biased,
                                 contribution_specification=specification)

def sa_pioglitazone_mpo() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = pioglitazone_mpo()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SAScoreModifier())
    return GoalDirectedBenchmark(name='SA_pioglitazone',
                                 objective=sa_biased,
                                 contribution_specification=specification)

def sc_qed_benchmark() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    sa_qed = ScoringFunctionSAWrapper(RdkitScoringFunction(descriptor=qed), SCScoreModifier())
    return GoalDirectedBenchmark(name='SC_QED',
                                 objective=sa_qed,
                                 contribution_specification=specification)

def sc_ranolazine_mpo() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = ranolazine_mpo()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SCScoreModifier())
    return GoalDirectedBenchmark(name='SC_ranolazine',
                                 objective=sa_biased,
                                 contribution_specification=specification)

def sc_cns_mpo() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = cns_mpo()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SCScoreModifier())
    return GoalDirectedBenchmark(name='SC_CNS',
                                 objective=sa_biased,
                                 contribution_specification=specification)

def sc_isomers_c7h8n2o2() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = isomers_c7h8n2o2()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SCScoreModifier())
    return GoalDirectedBenchmark(name='SC_isomer',
                                 objective=sa_biased,
                                 contribution_specification=specification)

def sc_pioglitazone_mpo() -> GoalDirectedBenchmark:
    specification = uniform_specification(1, 10, 100)
    benchmark_object = pioglitazone_mpo()
    sa_biased = ScoringFunctionSAWrapper(benchmark_object.objective, SCScoreModifier())
    return GoalDirectedBenchmark(name='SC_pioglitazone',
                                 objective=sa_biased,
                                 contribution_specification=specification)
