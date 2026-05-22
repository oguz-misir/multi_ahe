/**
 * Phase 5 validator — sends a NavigateToPose goal to one robot and prints result.
 * Usage: ros2 run m_ahe_mrta_bringup nav2_goal_sender <robot_ns> <x> <y>
 */
#include <chrono>
#include <memory>
#include <string>

#include "geometry_msgs/msg/pose_stamped.hpp"
#include "nav2_msgs/action/navigate_to_pose.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"

using NavigateToPose = nav2_msgs::action::NavigateToPose;
using GoalHandleNav = rclcpp_action::ClientGoalHandle<NavigateToPose>;
using namespace std::chrono_literals;

int main(int argc, char** argv)
{
    rclcpp::init(argc, argv);

    if (argc != 4) {
        fprintf(stderr, "Usage: nav2_goal_sender <robot_ns> <x> <y>\n");
        rclcpp::shutdown();
        return 1;
    }

    std::string robot_ns = argv[1];
    double x = std::stod(argv[2]);
    double y = std::stod(argv[3]);
    std::string action_name = "/" + robot_ns + "/navigate_to_pose";

    auto node = rclcpp::Node::make_shared("nav2_goal_sender");
    auto client = rclcpp_action::create_client<NavigateToPose>(node, action_name);

    RCLCPP_INFO(node->get_logger(), "Waiting for %s ...", action_name.c_str());
    if (!client->wait_for_action_server(15s)) {
        RCLCPP_ERROR(node->get_logger(), "Action server not available");
        rclcpp::shutdown();
        return 1;
    }

    auto goal = NavigateToPose::Goal();
    goal.pose.header.frame_id = robot_ns + "/map";
    goal.pose.pose.position.x = x;
    goal.pose.pose.position.y = y;
    goal.pose.pose.orientation.w = 1.0;

    RCLCPP_INFO(node->get_logger(), "Sending goal (%.2f, %.2f) to %s", x, y, robot_ns.c_str());

    rclcpp_action::Client<NavigateToPose>::SendGoalOptions opts;
    opts.feedback_callback = [&](GoalHandleNav::SharedPtr,
                                 const std::shared_ptr<const NavigateToPose::Feedback> fb) {
        RCLCPP_INFO(node->get_logger(), "  distance_remaining: %.2f m",
                    fb->distance_remaining);
    };

    bool done = false;
    bool succeeded = false;
    opts.result_callback = [&](const GoalHandleNav::WrappedResult& result) {
        if (result.code == rclcpp_action::ResultCode::SUCCEEDED) {
            RCLCPP_INFO(node->get_logger(), "GOAL SUCCEEDED");
            succeeded = true;
        } else {
            RCLCPP_ERROR(node->get_logger(), "GOAL FAILED (code %d)",
                         static_cast<int>(result.code));
        }
        done = true;
    };

    auto gh_future = client->async_send_goal(goal, opts);
    if (rclcpp::spin_until_future_complete(node, gh_future, 15s) !=
        rclcpp::FutureReturnCode::SUCCESS)
    {
        RCLCPP_ERROR(node->get_logger(), "Goal send timed out");
        rclcpp::shutdown();
        return 1;
    }
    auto gh = gh_future.get();
    if (!gh) {
        RCLCPP_ERROR(node->get_logger(), "Goal rejected");
        rclcpp::shutdown();
        return 1;
    }

    RCLCPP_INFO(node->get_logger(), "Goal accepted — waiting for result (max 120s)...");
    auto result_future = client->async_get_result(gh);
    if (rclcpp::spin_until_future_complete(node, result_future, 120s) !=
        rclcpp::FutureReturnCode::SUCCESS)
    {
        RCLCPP_ERROR(node->get_logger(), "Result timed out");
        rclcpp::shutdown();
        return 1;
    }

    rclcpp::shutdown();
    return succeeded ? 0 : 1;
}
