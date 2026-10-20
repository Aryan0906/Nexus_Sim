#include <gtest/gtest.h>
#include "../src/agent/SignalController.h"
#include "../src/agent/FuzzyPolicy.h"
#include "../src/agent/Type2FuzzyPolicy.h"
#include "../src/agent/SymbolicRulePolicy.h"
#include <memory>

using namespace nexussim;

class FuzzyPolicyTest : public ::testing::Test {
protected:
    void SetUp() override {
        sc = std::make_unique<SignalController>(101);
        std::vector<std::vector<int64_t>> phase_edges = {{10, 11}, {12, 13}};
        std::vector<double> phase_volumes = {500.0, 500.0};
        sc->calculate_webster_timing(phase_edges, phase_volumes);
        fuzzy = std::make_unique<FuzzyPolicy>(sc.get());
    }

    std::unique_ptr<SignalController> sc;
    std::unique_ptr<FuzzyPolicy> fuzzy;
};

TEST_F(FuzzyPolicyTest, PolicyNameReturnsFuzzy) {
    EXPECT_EQ(fuzzy->policy_name(), "fuzzy");
}

TEST_F(FuzzyPolicyTest, ZeroQueueZeroWaitGivesZeroExtension) {
    double ext = fuzzy->compute_green_extension(0.0, 0.0);
    EXPECT_NEAR(ext, 0.0, 1e-3);
}

TEST_F(FuzzyPolicyTest, MaxQueueMaxWaitGivesMaxExtension) {
    double ext = fuzzy->compute_green_extension(50.0, 300.0);
    EXPECT_NEAR(ext, 15.0, 1e-3);
}

TEST_F(FuzzyPolicyTest, MediumQueueMediumWaitGivesMidExtension) {
    double ext = fuzzy->compute_green_extension(15.0, 60.0);
    EXPECT_GT(ext, 2.0);
    EXPECT_LT(ext, 10.0);
}

TEST_F(FuzzyPolicyTest, DefuzzifiedRangeIsBounded) {
    for (double q = 0.0; q <= 60.0; q += 15.0) {
        for (double w = 0.0; w <= 350.0; w += 50.0) {
            double ext = fuzzy->compute_green_extension(q, w);
            EXPECT_GE(ext, 0.0);
            EXPECT_LE(ext, 15.0);
        }
    }
}

TEST_F(FuzzyPolicyTest, IsGreenMatchesControllerState) {
    EXPECT_TRUE(fuzzy->is_green(10));
    EXPECT_FALSE(fuzzy->is_green(12));
}

TEST_F(FuzzyPolicyTest, CurrentPhaseIndexMatchesController) {
    EXPECT_EQ(fuzzy->current_phase_index(), 0);
}

TEST(Type2FuzzyPolicyTest, PolicyNameAndBounds) {
    auto sc = std::make_unique<SignalController>(102);
    Type2FuzzyPolicy policy(sc.get());
    EXPECT_EQ(policy.policy_name(), "type2_fuzzy");

    double zero_ext = policy.compute_green_extension(0.0, 0.0);
    EXPECT_GE(zero_ext, 0.0);
    EXPECT_LE(zero_ext, 15.0);

    double high_ext = policy.compute_green_extension(50.0, 300.0);
    EXPECT_GE(high_ext, zero_ext);
    EXPECT_LE(high_ext, 15.0);
}

TEST(SymbolicRulePolicyTest, DecisionTreeRuleFiring) {
    auto sc = std::make_unique<SignalController>(103);
    SymbolicRulePolicy policy(sc.get());
    EXPECT_EQ(policy.policy_name(), "symbolic_gp");

    // EXTEND (0) when queue <= 8.5
    EXPECT_EQ(policy.evaluate_symbolic_rule({5.0f, 0.0f, 10.0f, 60.0f}), 0);

    // EXTEND (0) when queue > 8.5 but wait <= 45.0
    EXPECT_EQ(policy.evaluate_symbolic_rule({15.0f, 0.0f, 10.0f, 30.0f}), 0);

    // SWITCH (1) when queue > 8.5 AND wait > 45.0
    EXPECT_EQ(policy.evaluate_symbolic_rule({15.0f, 0.0f, 10.0f, 60.0f}), 1);
}

namespace {

// Tick a policy until its controller leaves GREEN, returning the tick count.
int ticks_until_yellow(SignalController& sc, SignalPolicy& policy,
                       double queue, double wait, double dt, int max_ticks) {
    policy.set_inputs(queue, wait);
    for (int i = 0; i < max_ticks; ++i) {
        policy.tick(dt);
        if (sc.current_state != SignalController::PhaseState::GREEN) return i;
    }
    return max_ticks;
}

} // namespace

// P4: prove the fuzzy policy actually alters signal timing (not just a label).
// Two identical controllers: fuzzy-with-demand must stay green at least 10 s
// longer than fuzzy-without-demand.
TEST(FuzzyPolicyWiringTest, HighDemandExtendsGreenBeyondLowDemand) {
    SignalController low(201);
    SignalController high(201);
    const std::vector<std::vector<int64_t>> edges = {{10, 11}, {12, 13}};
    const std::vector<double> volumes = {500.0, 500.0};
    low.calculate_webster_timing(edges, volumes);
    high.calculate_webster_timing(edges, volumes);

    FuzzyPolicy low_policy(&low);
    FuzzyPolicy high_policy(&high);

    const double dt = 0.1;
    const int max_ticks = 1000; // 100 s
    const int low_ticks = ticks_until_yellow(low, low_policy, 0.0, 0.0, dt, max_ticks);
    const int high_ticks = ticks_until_yellow(high, high_policy, 40.0, 120.0, dt, max_ticks);

    ASSERT_LT(low_ticks, max_ticks);
    ASSERT_LT(high_ticks, max_ticks);
    EXPECT_GE((high_ticks - low_ticks) * dt, 10.0)
        << "high-demand fuzzy control must extend green by at least 10 s";
}

TEST(FuzzyPolicyWiringTest, ExtensionBudgetIsCappedAtFifteenSeconds) {
    SignalController sc(202);
    sc.calculate_webster_timing({{10, 11}, {12, 13}}, {500.0, 500.0});
    FuzzyPolicy policy(&sc);
    const double dt = 0.1;

    // Force repeated imminent expiries; the 15 s budget must stop extending.
    int forced = 0;
    while (sc.current_state == SignalController::PhaseState::GREEN && forced < 10) {
        sc.current_timer = dt * 0.5;
        policy.set_inputs(40.0, 120.0);
        policy.tick(dt);
        ++forced;
    }
    EXPECT_NE(sc.current_state, SignalController::PhaseState::GREEN)
        << "extension budget must eventually release the phase";
    EXPECT_LE(forced, 4) << "15 s budget should be consumed in a few extensions";
}

TEST(FuzzyPolicyWiringTest, Type2HighDemandAlsoExtendsGreen) {
    SignalController low(203);
    SignalController high(203);
    const std::vector<std::vector<int64_t>> edges = {{10, 11}, {12, 13}};
    const std::vector<double> volumes = {500.0, 500.0};
    low.calculate_webster_timing(edges, volumes);
    high.calculate_webster_timing(edges, volumes);

    Type2FuzzyPolicy low_policy(&low);
    Type2FuzzyPolicy high_policy(&high);

    const double dt = 0.1;
    const int max_ticks = 1000;
    const int low_ticks = ticks_until_yellow(low, low_policy, 0.0, 0.0, dt, max_ticks);
    const int high_ticks = ticks_until_yellow(high, high_policy, 40.0, 120.0, dt, max_ticks);

    ASSERT_LT(low_ticks, max_ticks);
    ASSERT_LT(high_ticks, max_ticks);
    EXPECT_GE((high_ticks - low_ticks) * dt, 10.0)
        << "type-2 fuzzy control must extend green under high demand";
}
